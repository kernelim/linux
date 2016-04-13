#ifndef _NET_DST_OPS_H
#define _NET_DST_OPS_H
#include <linux/types.h>
#include <linux/rcupdate.h>

struct dst_entry;
struct kmem_cachep;
struct net_device;
struct sk_buff;

struct dst_ops {
	unsigned short		family;
	__be16			protocol;
	unsigned		gc_thresh;

	int			(*gc)(struct dst_ops *ops);
	struct dst_entry *	(*check)(struct dst_entry *, __u32 cookie);
	void			(*destroy)(struct dst_entry *);
	void			(*ifdown)(struct dst_entry *,
					  struct net_device *dev, int how);
	struct dst_entry *	(*negative_advice)(struct dst_entry *);
	void			(*link_failure)(struct sk_buff *);
	void			(*update_pmtu)(struct dst_entry *dst, u32 mtu);
	int			(*local_out)(struct sk_buff *skb);

	atomic_t		entries;
	struct kmem_cache	*kmem_cachep;
};

struct dst_ops_extend {
	struct list_head list;
	const struct dst_ops *key;
	unsigned int (*default_advmss)(const struct dst_entry *);
	struct rcu_head rcu;
};

struct dst_ops_extend *dst_ops_extend_get_rcu(struct dst_ops *key);
int dst_ops_extend_register(struct dst_ops *key, unsigned int (*default_advmss)(const struct dst_entry *));
void dst_ops_extend_unregister(struct dst_ops *key);

#endif
