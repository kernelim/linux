/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _NF_CONNTRACK_COMMON_H
#define _NF_CONNTRACK_COMMON_H

#include <uapi/linux/netfilter/nf_conntrack_common.h>

#include <linux/rh_kabi.h>

struct ip_conntrack_stat {
	unsigned int found;
	unsigned int invalid;
	RH_KABI_REPLACE(unsigned int ignore, unsigned int clash_resolve)
	unsigned int insert;
	unsigned int insert_failed;
	unsigned int drop;
	unsigned int early_drop;
	unsigned int error;
	unsigned int expect_new;
	unsigned int expect_create;
	unsigned int expect_delete;
	unsigned int search_restart;
};

#endif /* _NF_CONNTRACK_COMMON_H */
