/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __NETNS_XDP_H__
#define __NETNS_XDP_H__

#include <linux/rculist.h>
#include <linux/mutex.h>

/* RHEL: The struct netns_xdp can be changed between releases and is not
 * kABI stable. */
struct netns_xdp {
	struct mutex		lock;
	struct hlist_head	list;
};

#endif /* __NETNS_XDP_H__ */
