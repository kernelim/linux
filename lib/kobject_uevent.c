/*
 * kernel userspace event delivery
 *
 * Copyright (C) 2004 Red Hat, Inc.  All rights reserved.
 * Copyright (C) 2004 Novell, Inc.  All rights reserved.
 * Copyright (C) 2004 IBM, Inc. All rights reserved.
 *
 * Licensed under the GNU GPL v2.
 *
 * Authors:
 *	Robert Love		<rml@novell.com>
 *	Kay Sievers		<kay.sievers@vrfy.org>
 *	Arjan van de Ven	<arjanv@redhat.com>
 *	Greg Kroah-Hartman	<greg@kroah.com>
 */

#include <linux/spinlock.h>
#include <linux/string.h>
#include <linux/kobject.h>
#include <linux/export.h>
#include <linux/kmod.h>
#include <linux/slab.h>
#include <linux/socket.h>
#include <linux/skbuff.h>
#include <linux/netlink.h>
#include <linux/uidgid.h>
#include <net/sock.h>
#include <net/net_namespace.h>


u64 uevent_seqnum;
#ifdef CONFIG_UEVENT_HELPER
char uevent_helper[UEVENT_HELPER_PATH_LEN] = CONFIG_UEVENT_HELPER_PATH;
#endif

struct uevent_sock {
	struct list_head list;
	struct sock *sk;
};

#ifdef CONFIG_NET
static LIST_HEAD(uevent_sock_list);
#endif

/* This lock protects uevent_seqnum and uevent_sock_list */
static DEFINE_MUTEX(uevent_sock_mutex);

/* the strings here must match the enum in include/linux/kobject.h */
static const char *kobject_actions[] = {
	[KOBJ_ADD] =		"add",
	[KOBJ_REMOVE] =		"remove",
	[KOBJ_CHANGE] =		"change",
	[KOBJ_MOVE] =		"move",
	[KOBJ_ONLINE] =		"online",
	[KOBJ_OFFLINE] =	"offline",
};

/**
 * kobject_action_type - translate action string to numeric type
 *
 * @buf: buffer containing the action string, newline is ignored
 * @count: length of buffer
 * @type: pointer to the location to store the action type
 *
 * Returns 0 if the action string was recognized.
 */
int kobject_action_type(const char *buf, size_t count,
			enum kobject_action *type)
{
	enum kobject_action action;
	int ret = -EINVAL;

	if (count && (buf[count-1] == '\n' || buf[count-1] == '\0'))
		count--;

	if (!count)
		goto out;

	for (action = 0; action < ARRAY_SIZE(kobject_actions); action++) {
		if (strncmp(kobject_actions[action], buf, count) != 0)
			continue;
		if (kobject_actions[action][count] != '\0')
			continue;
		*type = action;
		ret = 0;
		break;
	}
out:
	return ret;
}

#ifdef CONFIG_UEVENT_HELPER
static int kobj_usermode_filter(struct kobject *kobj)
{
	const struct kobj_ns_type_operations *ops;

	ops = kobj_ns_ops(kobj);
	if (ops) {
		const void *init_ns, *ns;
		ns = kobj->ktype->namespace(kobj);
		init_ns = ops->initial_ns();
		return ns != init_ns;
	}

	return 0;
}

static int init_uevent_argv(struct kobj_uevent_env *env, const char *subsystem)
{
	int len;

	len = strlcpy(&env->buf[env->buflen], subsystem,
		      sizeof(env->buf) - env->buflen);
	if (len >= (sizeof(env->buf) - env->buflen)) {
		WARN(1, KERN_ERR "init_uevent_argv: buffer size too small\n");
		return -ENOMEM;
	}

	env->argv[0] = uevent_helper;
	env->argv[1] = &env->buf[env->buflen];
	env->argv[2] = NULL;

	env->buflen += len + 1;
	return 0;
}

static void cleanup_uevent_env(struct subprocess_info *info)
{
	kfree(info->data);
}
#endif

#ifdef CONFIG_NET
static struct sk_buff *alloc_uevent_skb(struct kobj_uevent_env *env,
					const char *action_string,
					const char *devpath)
{
	struct netlink_skb_parms *parms;
	struct sk_buff *skb = NULL;
	char *scratch;
	size_t len;

	/* allocate message with maximum possible size */
	len = strlen(action_string) + strlen(devpath) + 2;
	skb = alloc_skb(len + env->buflen, GFP_KERNEL);
	if (!skb)
		return NULL;

	/* add header */
	scratch = skb_put(skb, len);
	sprintf(scratch, "%s@%s", action_string, devpath);

	skb_put_data(skb, env->buf, env->buflen);

	parms = &NETLINK_CB(skb);
	parms->creds.uid = GLOBAL_ROOT_UID;
	parms->creds.gid = GLOBAL_ROOT_GID;
	parms->dst_group = 1;
	parms->portid = 0;

	return skb;
}

static int uevent_net_broadcast_untagged(struct kobj_uevent_env *env,
					 const char *action_string,
					 const char *devpath)
{
	struct sk_buff *skb = NULL;
	struct uevent_sock *ue_sk;
	int retval = 0;

	/* send netlink message */
	list_for_each_entry(ue_sk, &uevent_sock_list, list) {
		struct sock *uevent_sock = ue_sk->sk;

		if (!netlink_has_listeners(uevent_sock, 1))
			continue;

		if (!skb) {
			retval = -ENOMEM;
			skb = alloc_uevent_skb(env, action_string, devpath);
			if (!skb)
				continue;
		}

		retval = netlink_broadcast(uevent_sock, skb_get(skb), 0, 1,
					   GFP_KERNEL);
		/* ENOBUFS should be handled in userspace */
		if (retval == -ENOBUFS || retval == -ESRCH)
			retval = 0;
	}
	consume_skb(skb);

	return retval;
}

static int uevent_net_broadcast_tagged(struct sock *usk,
				       struct kobj_uevent_env *env,
				       const char *action_string,
				       const char *devpath)
{
	struct user_namespace *owning_user_ns = sock_net(usk)->user_ns;
	struct sk_buff *skb = NULL;
	int ret = 0;

	skb = alloc_uevent_skb(env, action_string, devpath);
	if (!skb)
		return -ENOMEM;

	/* fix credentials */
	if (owning_user_ns != &init_user_ns) {
		struct netlink_skb_parms *parms = &NETLINK_CB(skb);
		kuid_t root_uid;
		kgid_t root_gid;

		/* fix uid */
		root_uid = make_kuid(owning_user_ns, 0);
		if (uid_valid(root_uid))
			parms->creds.uid = root_uid;

		/* fix gid */
		root_gid = make_kgid(owning_user_ns, 0);
		if (gid_valid(root_gid))
			parms->creds.gid = root_gid;
	}

	ret = netlink_broadcast(usk, skb, 0, 1, GFP_KERNEL);
	/* ENOBUFS should be handled in userspace */
	if (ret == -ENOBUFS || ret == -ESRCH)
		ret = 0;

	return ret;
}
#endif

static int kobject_uevent_net_broadcast(struct kobject *kobj,
					struct kobj_uevent_env *env,
					const char *action_string,
					const char *devpath)
{
	int ret = 0;

#ifdef CONFIG_NET
	const struct kobj_ns_type_operations *ops;
	const struct net *net = NULL;

	ops = kobj_ns_ops(kobj);
	if (!ops && kobj->kset) {
		struct kobject *ksobj = &kobj->kset->kobj;
		if (ksobj->parent != NULL)
			ops = kobj_ns_ops(ksobj->parent);
	}

	/* kobjects currently only carry network namespace tags and they
	 * are the only tag relevant here since we want to decide which
	 * network namespaces to broadcast the uevent into.
	 */
	if (ops && ops->netlink_ns && kobj->ktype->namespace)
		if (ops->type == KOBJ_NS_TYPE_NET)
			net = kobj->ktype->namespace(kobj);

	if (!net)
		ret = uevent_net_broadcast_untagged(env, action_string,
						    devpath);
	else
		ret = uevent_net_broadcast_tagged(net->uevent_sock->sk, env,
						  action_string, devpath);
#endif

	return ret;
}

/**
 * kobject_uevent_env - send an uevent with environmental data
 *
 * @kobj: struct kobject that the action is happening to
 * @action: action that is happening
 * @envp_ext: pointer to environmental data
 *
 * Returns 0 if kobject_uevent_env() is completed with success or the
 * corresponding error when it fails.
 */
int kobject_uevent_env(struct kobject *kobj, enum kobject_action action,
		       char *envp_ext[])
{
	struct kobj_uevent_env *env;
	const char *action_string = kobject_actions[action];
	const char *devpath = NULL;
	const char *subsystem;
	struct kobject *top_kobj;
	struct kset *kset;
	const struct kset_uevent_ops *uevent_ops;
	int i = 0;
	int retval = 0;

	pr_debug("kobject: '%s' (%p): %s\n",
		 kobject_name(kobj), kobj, __func__);

	/* search the kset we belong to */
	top_kobj = kobj;
	while (!top_kobj->kset && top_kobj->parent)
		top_kobj = top_kobj->parent;

	if (!top_kobj->kset) {
		pr_debug("kobject: '%s' (%p): %s: attempted to send uevent "
			 "without kset!\n", kobject_name(kobj), kobj,
			 __func__);
		return -EINVAL;
	}

	kset = top_kobj->kset;
	uevent_ops = kset->uevent_ops;

	/* skip the event, if uevent_suppress is set*/
	if (kobj->uevent_suppress) {
		pr_debug("kobject: '%s' (%p): %s: uevent_suppress "
				 "caused the event to drop!\n",
				 kobject_name(kobj), kobj, __func__);
		return 0;
	}
	/* skip the event, if the filter returns zero. */
	if (uevent_ops && uevent_ops->filter)
		if (!uevent_ops->filter(kset, kobj)) {
			pr_debug("kobject: '%s' (%p): %s: filter function "
				 "caused the event to drop!\n",
				 kobject_name(kobj), kobj, __func__);
			return 0;
		}

	/* originating subsystem */
	if (uevent_ops && uevent_ops->name)
		subsystem = uevent_ops->name(kset, kobj);
	else
		subsystem = kobject_name(&kset->kobj);
	if (!subsystem) {
		pr_debug("kobject: '%s' (%p): %s: unset subsystem caused the "
			 "event to drop!\n", kobject_name(kobj), kobj,
			 __func__);
		return 0;
	}

	/* environment buffer */
	env = kzalloc(sizeof(struct kobj_uevent_env), GFP_KERNEL);
	if (!env)
		return -ENOMEM;

	/* complete object path */
	devpath = kobject_get_path(kobj, GFP_KERNEL);
	if (!devpath) {
		retval = -ENOENT;
		goto exit;
	}

	/* default keys */
	retval = add_uevent_var(env, "ACTION=%s", action_string);
	if (retval)
		goto exit;
	retval = add_uevent_var(env, "DEVPATH=%s", devpath);
	if (retval)
		goto exit;
	retval = add_uevent_var(env, "SUBSYSTEM=%s", subsystem);
	if (retval)
		goto exit;

	/* keys passed in from the caller */
	if (envp_ext) {
		for (i = 0; envp_ext[i]; i++) {
			retval = add_uevent_var(env, "%s", envp_ext[i]);
			if (retval)
				goto exit;
		}
	}

	/* let the kset specific function add its stuff */
	if (uevent_ops && uevent_ops->uevent) {
		retval = uevent_ops->uevent(kset, kobj, env);
		if (retval) {
			pr_debug("kobject: '%s' (%p): %s: uevent() returned "
				 "%d\n", kobject_name(kobj), kobj,
				 __func__, retval);
			goto exit;
		}
	}

	/*
	 * Mark "add" and "remove" events in the object to ensure proper
	 * events to userspace during automatic cleanup. If the object did
	 * send an "add" event, "remove" will automatically generated by
	 * the core, if not already done by the caller.
	 */
	if (action == KOBJ_ADD)
		kobj->state_add_uevent_sent = 1;
	else if (action == KOBJ_REMOVE)
		kobj->state_remove_uevent_sent = 1;

	mutex_lock(&uevent_sock_mutex);
	/* we will send an event, so request a new sequence number */
	retval = add_uevent_var(env, "SEQNUM=%llu", (unsigned long long)++uevent_seqnum);
	if (retval) {
		mutex_unlock(&uevent_sock_mutex);
		goto exit;
	}
	retval = kobject_uevent_net_broadcast(kobj, env, action_string,
					      devpath);
	mutex_unlock(&uevent_sock_mutex);

#ifdef CONFIG_UEVENT_HELPER
	/* call uevent_helper, usually only enabled during early boot */
	if (uevent_helper[0] && !kobj_usermode_filter(kobj)) {
		struct subprocess_info *info;

		retval = add_uevent_var(env, "HOME=/");
		if (retval)
			goto exit;
		retval = add_uevent_var(env,
					"PATH=/sbin:/bin:/usr/sbin:/usr/bin");
		if (retval)
			goto exit;
		retval = init_uevent_argv(env, subsystem);
		if (retval)
			goto exit;

		retval = -ENOMEM;
		info = call_usermodehelper_setup(env->argv[0], env->argv,
						 env->envp, GFP_KERNEL,
						 NULL, cleanup_uevent_env, env);
		if (info) {
			retval = call_usermodehelper_exec(info, UMH_NO_WAIT);
			env = NULL;	/* freed by cleanup_uevent_env */
		}
	}
#endif

exit:
	kfree(devpath);
	kfree(env);
	return retval;
}
EXPORT_SYMBOL_GPL(kobject_uevent_env);

/**
 * kobject_uevent - notify userspace by sending an uevent
 *
 * @kobj: struct kobject that the action is happening to
 * @action: action that is happening
 *
 * Returns 0 if kobject_uevent() is completed with success or the
 * corresponding error when it fails.
 */
int kobject_uevent(struct kobject *kobj, enum kobject_action action)
{
	return kobject_uevent_env(kobj, action, NULL);
}
EXPORT_SYMBOL_GPL(kobject_uevent);

/**
 * add_uevent_var - add key value string to the environment buffer
 * @env: environment buffer structure
 * @format: printf format for the key=value pair
 *
 * Returns 0 if environment variable was added successfully or -ENOMEM
 * if no space was available.
 */
int add_uevent_var(struct kobj_uevent_env *env, const char *format, ...)
{
	va_list args;
	int len;

	if (env->envp_idx >= ARRAY_SIZE(env->envp)) {
		WARN(1, KERN_ERR "add_uevent_var: too many keys\n");
		return -ENOMEM;
	}

	va_start(args, format);
	len = vsnprintf(&env->buf[env->buflen],
			sizeof(env->buf) - env->buflen,
			format, args);
	va_end(args);

	if (len >= (sizeof(env->buf) - env->buflen)) {
		WARN(1, KERN_ERR "add_uevent_var: buffer size too small\n");
		return -ENOMEM;
	}

	env->envp[env->envp_idx++] = &env->buf[env->buflen];
	env->buflen += len + 1;
	return 0;
}
EXPORT_SYMBOL_GPL(add_uevent_var);

#if defined(CONFIG_NET)
static int uevent_net_init(struct net *net)
{
	struct uevent_sock *ue_sk;
	struct netlink_kernel_cfg cfg = {
		.groups	= 1,
		.flags	= NL_CFG_F_NONROOT_RECV,
	};

	ue_sk = kzalloc(sizeof(*ue_sk), GFP_KERNEL);
	if (!ue_sk)
		return -ENOMEM;

	ue_sk->sk = netlink_kernel_create(net, NETLINK_KOBJECT_UEVENT, &cfg);
	if (!ue_sk->sk) {
		printk(KERN_ERR
		       "kobject_uevent: unable to create netlink socket!\n");
		kfree(ue_sk);
		return -ENODEV;
	}

	net->uevent_sock = ue_sk;

	/* Restrict uevents to initial user namespace. */
	if (sock_net(ue_sk->sk)->user_ns == &init_user_ns) {
		mutex_lock(&uevent_sock_mutex);
		list_add_tail(&ue_sk->list, &uevent_sock_list);
		mutex_unlock(&uevent_sock_mutex);
	}

	return 0;
}

static void uevent_net_exit(struct net *net)
{
	struct uevent_sock *ue_sk = net->uevent_sock;

	if (sock_net(ue_sk->sk)->user_ns == &init_user_ns) {
		mutex_lock(&uevent_sock_mutex);
		list_del(&ue_sk->list);
		mutex_unlock(&uevent_sock_mutex);
	}

	netlink_kernel_release(ue_sk->sk);
	kfree(ue_sk);
}

static struct pernet_operations uevent_net_ops = {
	.init	= uevent_net_init,
	.exit	= uevent_net_exit,
};

static int __init kobject_uevent_init(void)
{
	return register_pernet_subsys(&uevent_net_ops);
}


postcore_initcall(kobject_uevent_init);
#endif
