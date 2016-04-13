#ifndef GENETLINK_COMPAT_H
#define GENETLINK_COMPAT_H

#include <net/genetlink.h>

struct compat_genl_info {
	struct genl_info *info;

	u32 snd_seq;
	union {
		u32 snd_portid;
		u32 snd_pid;
	};
	struct genlmsghdr *genlhdr;
	struct nlattr **attrs;
	void *user_ptr[2];
};
#define genl_info compat_genl_info

struct compat_genl_ops {
	struct genl_ops ops;

	u8 cmd;
	u8 internal_flags;
	unsigned int flags;
	const struct nla_policy *policy;

	int (*doit)(struct sk_buff *skb, struct genl_info *info);
	int (*dumpit)(struct sk_buff *skb, struct netlink_callback *cb);
	int (*done)(struct netlink_callback *cb);
};
#define genl_ops compat_genl_ops

struct compat_genl_family {
	struct genl_family family;
	struct list_head list;

	unsigned int id, hdrsize, version, maxattr;
	char name[GENL_NAMSIZ];
	bool netnsok;
	bool parallel_ops;

	struct nlattr **attrbuf;

	int (*pre_doit)(const struct genl_ops *ops, struct sk_buff *skb,
			struct genl_info *info);

	void (*post_doit)(const struct genl_ops *ops, struct sk_buff *skb,
			  struct genl_info *info);

	struct genl_multicast_group *mcgrps;
	struct genl_ops *ops;
	unsigned int n_mcgrps, n_ops;

	struct module *module;
};
#define genl_family compat_genl_family

extern int compat_genl_register_family(struct genl_family *family);

static inline int
_genl_register_family_with_ops_grps(struct genl_family *family,
				    struct genl_ops *ops, size_t n_ops,
				    struct genl_multicast_group *mcgrps,
				    size_t n_mcgrps)
{
	family->module = THIS_MODULE;
	family->ops = ops;
	family->n_ops = n_ops;
	family->mcgrps = mcgrps;
	family->n_mcgrps = n_mcgrps;
	return compat_genl_register_family(family);
}

#define genl_register_family_with_ops_groups(family, ops, grps)	\
	_genl_register_family_with_ops_grps((family),			\
					    (ops), ARRAY_SIZE(ops),	\
					    (grps), ARRAY_SIZE(grps))

#define genl_unregister_family compat_genl_unregister_family

int genl_unregister_family(struct genl_family *family);

#define genl_info_net(_info) genl_info_net((_info)->info)

#define genlmsg_reply(_msg, _info) genlmsg_reply(_msg, (_info)->info)
#define genlmsg_put(_skb, _pid, _seq, _fam, _flags, _cmd) genlmsg_put(_skb, _pid, _seq, &(_fam)->family, _flags, _cmd)
#define genl_register_mc_group(_fam, _grp) genl_register_mc_group(&(_fam)->family, _grp)
#define genl_unregister_mc_group(_fam, _grp) genl_unregister_mc_group(&(_fam)->family, _grp)
#define genl_dump_check_consistent(cb, user_hdr, _fam) genl_dump_check_consistent(cb, user_hdr, &(_fam)->family)

static inline int
compat_genlmsg_multicast_netns(struct genl_family *family,
			       struct net *net, struct sk_buff *skb,
			       u32 portid, unsigned int group,
			       gfp_t flags)
{
	if (WARN_ON_ONCE(group >= family->n_mcgrps))
		return -EINVAL;
	group = family->mcgrps[group].id;
	return nlmsg_multicast(net->genl_sock,skb, portid, group, flags);
}
#define genlmsg_multicast_netns compat_genlmsg_multicast_netns 

static inline int
compat_genlmsg_multicast_allns(struct genl_family *family,
				 struct sk_buff *skb, u32 portid,
				 unsigned int group, gfp_t flags)
{
	if (WARN_ON_ONCE(group >= family->n_mcgrps))
		return -EINVAL;
	group = family->mcgrps[group].id;
	return genlmsg_multicast_allns(skb, portid, group, flags);
}
#define genlmsg_multicast_allns compat_genlmsg_multicast_allns

#endif /* GENETLINK_COMPAT_H */
