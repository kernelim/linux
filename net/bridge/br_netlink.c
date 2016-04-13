/*
 *	Bridge netlink control interface
 *
 *	Authors:
 *	Stephen Hemminger		<shemminger@osdl.org>
 *
 *	This program is free software; you can redistribute it and/or
 *	modify it under the terms of the GNU General Public License
 *	as published by the Free Software Foundation; either version
 *	2 of the License, or (at your option) any later version.
 */

#include <linux/kernel.h>
#include <linux/etherdevice.h>
#include <net/rtnetlink.h>
#include <net/net_namespace.h>
#include <net/sock.h>

#include "br_private.h"
#include "br_private_stp.h"

static inline size_t br_port_info_size(void)
{
	return nla_total_size(1)	/* IFLA_BRPORT_STATE  */
		+ nla_total_size(2)	/* IFLA_BRPORT_PRIORITY */
		+ nla_total_size(4)	/* IFLA_BRPORT_COST */
		+ nla_total_size(1)	/* IFLA_BRPORT_MODE */
		+ 0;
}

static inline size_t br_nlmsg_size(void)
{
	return NLMSG_ALIGN(sizeof(struct ifinfomsg))
		+ nla_total_size(IFNAMSIZ) /* IFLA_IFNAME */
		+ nla_total_size(MAX_ADDR_LEN) /* IFLA_ADDRESS */
		+ nla_total_size(4) /* IFLA_MASTER */
		+ nla_total_size(4) /* IFLA_MTU */
		+ nla_total_size(4) /* IFLA_LINK */
		+ nla_total_size(1) /* IFLA_OPERSTATE */
		+ nla_total_size(br_port_info_size()); /* IFLA_PROTINFO */
}

static int br_port_fill_attrs(struct sk_buff *skb,
			      const struct net_bridge_port *p)
{
	u8 mode = !!(p->flags & BR_HAIRPIN_MODE);

	if (nla_put_u8(skb, IFLA_BRPORT_STATE, p->state) ||
	    nla_put_u16(skb, IFLA_BRPORT_PRIORITY, p->priority) ||
	    nla_put_u32(skb, IFLA_BRPORT_COST, p->path_cost) ||
	    nla_put_u8(skb, IFLA_BRPORT_MODE, mode))
		return -EMSGSIZE;

	return 0;
}

/*
 * Create one netlink message for one interface
 * Contains port and master info as well as carrier and bridge state.
 */
static int br_fill_ifinfo(struct sk_buff *skb, const struct net_bridge_port *port,
			  u32 pid, u32 seq, int event, unsigned int flags)
{
	const struct net_bridge *br = port->br;
	const struct net_device *dev = port->dev;
	struct ifinfomsg *hdr;
	struct nlmsghdr *nlh;
	u8 operstate = netif_running(dev) ? dev->operstate : IF_OPER_DOWN;

	pr_debug("br_fill_info event %d port %s master %s\n",
		 event, dev->name, br->dev->name);

	nlh = nlmsg_put(skb, pid, seq, event, sizeof(*hdr), flags);
	if (nlh == NULL)
		return -EMSGSIZE;

	hdr = nlmsg_data(nlh);
	hdr->ifi_family = AF_BRIDGE;
	hdr->__ifi_pad = 0;
	hdr->ifi_type = dev->type;
	hdr->ifi_index = dev->ifindex;
	hdr->ifi_flags = dev_get_flags(dev);
	hdr->ifi_change = 0;

	NLA_PUT_STRING(skb, IFLA_IFNAME, dev->name);
	NLA_PUT_U32(skb, IFLA_MASTER, br->dev->ifindex);
	NLA_PUT_U32(skb, IFLA_MTU, dev->mtu);
	NLA_PUT_U8(skb, IFLA_OPERSTATE, operstate);

	if (dev->addr_len)
		NLA_PUT(skb, IFLA_ADDRESS, dev->addr_len, dev->dev_addr);

	if (dev->ifindex != dev->iflink)
		NLA_PUT_U32(skb, IFLA_LINK, dev->iflink);

	if (event == RTM_NEWLINK) {
		struct nlattr *nest
			= nla_nest_start(skb, IFLA_PROTINFO | NLA_F_NESTED);

		if (nest == NULL || br_port_fill_attrs(skb, port) < 0)
			goto nla_put_failure;
		nla_nest_end(skb, nest);
	}

	return nlmsg_end(skb, nlh);

nla_put_failure:
	nlmsg_cancel(skb, nlh);
	return -EMSGSIZE;
}

/*
 * Notify listeners of a change in port information
 */
void br_ifinfo_notify(int event, struct net_bridge_port *port)
{
	struct net *net = dev_net(port->dev);
	struct sk_buff *skb;
	int err = -ENOBUFS;

	pr_debug("bridge notify event=%d\n", event);
	skb = nlmsg_new(br_nlmsg_size(), GFP_ATOMIC);
	if (skb == NULL)
		goto errout;

	err = br_fill_ifinfo(skb, port, 0, 0, event, 0);
	if (err < 0) {
		/* -EMSGSIZE implies BUG in br_nlmsg_size() */
		WARN_ON(err == -EMSGSIZE);
		kfree_skb(skb);
		goto errout;
	}
	rtnl_notify(skb, net, 0, RTNLGRP_LINK, NULL, GFP_ATOMIC);
	return;
errout:
	if (err < 0)
		rtnl_set_sk_err(net, RTNLGRP_LINK, err);
}

/*
 * Dump information about all ports, in response to GETLINK
 */
static int br_dump_ifinfo(struct sk_buff *skb, struct netlink_callback *cb)
{
	struct net *net = sock_net(skb->sk);
	struct net_device *dev;
	int idx;

	idx = 0;
	for_each_netdev(net, dev) {
		/* not a bridge port */
		if (dev->br_port == NULL || idx < cb->args[0])
			goto skip;

		if (br_fill_ifinfo(skb, dev->br_port, NETLINK_CB(cb->skb).pid,
				   cb->nlh->nlmsg_seq, RTM_NEWLINK,
				   NLM_F_MULTI) < 0)
			break;
skip:
		++idx;
	}

	cb->args[0] = idx;

	return skb->len;
}

static size_t br_get_size(const struct net_device *brdev)
{
	return nla_total_size(sizeof(u32)) +	/* IFLA_BR_FORWARD_DELAY  */
	       nla_total_size(sizeof(u32)) +	/* IFLA_BR_HELLO_TIME */
	       nla_total_size(sizeof(u32)) +	/* IFLA_BR_MAX_AGE */
	       0;
}

static int br_fill_info(struct sk_buff *skb, const struct net_device *brdev)
{
	struct net_bridge *br = netdev_priv(brdev);
	u32 forward_delay = jiffies_to_clock_t(br->forward_delay);
	u32 hello_time = jiffies_to_clock_t(br->hello_time);
	u32 age_time = jiffies_to_clock_t(br->max_age);

	if (nla_put_u32(skb, IFLA_BR_FORWARD_DELAY, forward_delay) ||
	    nla_put_u32(skb, IFLA_BR_HELLO_TIME, hello_time) ||
	    nla_put_u32(skb, IFLA_BR_MAX_AGE, age_time))
		return -EMSGSIZE;

	return 0;
}

static const struct nla_policy ifla_brport_policy[IFLA_BRPORT_MAX + 1] = {
	[IFLA_BRPORT_STATE]	= { .type = NLA_U8 },
	[IFLA_BRPORT_COST]	= { .type = NLA_U32 },
	[IFLA_BRPORT_PRIORITY]	= { .type = NLA_U16 },
	[IFLA_BRPORT_MODE]	= { .type = NLA_U8 },
};

/* Change the state of the port and notify spanning tree */
static int br_set_port_state(struct net_bridge_port *p, u8 state)
{
	if (state > BR_STATE_BLOCKING)
		return -EINVAL;

	/* if kernel STP is running, don't allow changes */
	if (p->br->stp_enabled == BR_KERNEL_STP)
		return -EBUSY;

	if (!netif_running(p->dev) ||
	    (!netif_carrier_ok(p->dev) && state != BR_STATE_DISABLED))
		return -ENETDOWN;

	p->state = state;
	br_log_state(p);
	br_port_state_selection(p->br);
	return 0;
}

/* Set/clear or port flags based on attribute */
static void br_set_port_flag(struct net_bridge_port *p, struct nlattr *tb[],
			   int attrtype, unsigned long mask)
{
	if (tb[attrtype]) {
		u8 flag = nla_get_u8(tb[attrtype]);
		if (flag)
			p->flags |= mask;
		else
			p->flags &= ~mask;
	}
}

/* Process bridge protocol info on port */
static int br_setport(struct net_bridge_port *p, struct nlattr *tb[])
{
	br_set_port_flag(p, tb, IFLA_BRPORT_MODE, BR_HAIRPIN_MODE);

	if (tb[IFLA_BRPORT_COST])
		br_stp_set_path_cost(p, nla_get_u32(tb[IFLA_BRPORT_COST]));

	if (tb[IFLA_BRPORT_PRIORITY])
		br_stp_set_port_priority(p, nla_get_u16(tb[IFLA_BRPORT_PRIORITY]));

	if (tb[IFLA_BRPORT_STATE])
		br_set_port_state(p, nla_get_u8(tb[IFLA_BRPORT_STATE]));

	return 0;
}

/* Change state and parameters on port. */
static int br_rtm_setlink(struct sk_buff *skb,  struct nlmsghdr *nlh, void *arg)
{
	struct net *net = sock_net(skb->sk);
	struct ifinfomsg *ifm;
	struct nlattr *protinfo;
	struct net_device *dev;
	struct net_bridge_port *p;
	struct nlattr *tb[IFLA_BRPORT_MAX];
	int err;

	if (nlmsg_len(nlh) < sizeof(*ifm))
		return -EINVAL;

	ifm = nlmsg_data(nlh);
	if (ifm->ifi_family != AF_BRIDGE)
		return -EPFNOSUPPORT;

	protinfo = nlmsg_find_attr(nlh, sizeof(*ifm), IFLA_PROTINFO);
	if (!protinfo)
		return 0;

	dev = __dev_get_by_index(net, ifm->ifi_index);
	if (!dev)
		return -ENODEV;

	p = dev->br_port;
	if (!p)
		return -EINVAL;

	if (protinfo->nla_type & NLA_F_NESTED) {
		err = nla_parse_nested(tb, IFLA_BRPORT_MAX,
				       protinfo, ifla_brport_policy);
		if (err)
			return err;

		spin_lock_bh(&p->br->lock);
		err = br_setport(p, tb);
		spin_unlock_bh(&p->br->lock);
	} else {
		/* Binary compatability with old RSTP */
		if (nla_len(protinfo) < sizeof(u8))
			return -EINVAL;

		spin_lock_bh(&p->br->lock);
		err = br_set_port_state(p, nla_get_u8(protinfo));
		spin_unlock_bh(&p->br->lock);
	}

	if (err == 0)
		br_ifinfo_notify(RTM_NEWLINK, p);

	return err;
}

static int br_validate(struct nlattr *tb[], struct nlattr *data[])
{
	if (tb[IFLA_ADDRESS]) {
		if (nla_len(tb[IFLA_ADDRESS]) != ETH_ALEN)
			return -EINVAL;
		if (!is_valid_ether_addr(nla_data(tb[IFLA_ADDRESS])))
			return -EADDRNOTAVAIL;
	}

	return 0;
}

struct rtnl_link_ops br_link_ops __read_mostly = {
	.kind		= "bridge",
	.priv_size	= sizeof(struct net_bridge),
	.setup		= br_dev_setup,
	.validate	= br_validate,
	.dellink	= br_dev_delete,
	.get_size	= br_get_size,
	.fill_info	= br_fill_info,
};

int __init br_netlink_init(void)
{
	int err;

	err = rtnl_link_register(&br_link_ops);
	if (err < 0)
		goto err1;

	/* be sure to remove RHEL-specific rtnl_unregister's in
	 * br_netlink_fini if you're backporting upstream commit
	 * e5a55a898720 */
	if (__rtnl_register(PF_BRIDGE, RTM_GETLINK, NULL,
			      br_dump_ifinfo, NULL))
		goto err2;

	/* Only the first call to __rtnl_register can fail */
	__rtnl_register(PF_BRIDGE, RTM_SETLINK,
			      br_rtm_setlink, NULL, NULL);

	br_mdb_init();
	return 0;

err2:
	rtnl_link_unregister(&br_link_ops);

err1:
	return err;
}

void __exit br_netlink_fini(void)
{
	rtnl_link_unregister(&br_link_ops);
	rtnl_unregister(PF_BRIDGE, RTM_SETLINK);
	rtnl_unregister(PF_BRIDGE, RTM_GETLINK);
	br_mdb_uninit();
}
