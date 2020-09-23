/*
 * Copyright (c) 2008, Intel Corporation.
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms and conditions of the GNU General Public License,
 * version 2, as published by the Free Software Foundation.
 *
 * This program is distributed in the hope it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 *
 * You should have received a copy of the GNU General Public License along with
 * this program; if not, see <http://www.gnu.org/licenses/>.
 *
 * Author: Alexander Duyck <alexander.h.duyck@intel.com>
 */

#ifndef __NET_TC_SKBEDIT_H
#define __NET_TC_SKBEDIT_H

#include <net/act_api.h>
#include <linux/tc_act/tc_skbedit.h>

struct tcf_skbedit_params {
	u32 flags;
	u32 priority;
	u32 mark;
	u32 mask;
	u16 queue_mapping;
	u16 ptype;
	struct rcu_head rcu;
};

struct tcf_skbedit {
	struct tc_action common;
	struct tcf_skbedit_params __rcu *params;
};
#define to_skbedit(a) ((struct tcf_skbedit *)a)

/* Return true iff action is the one identified by FLAG. */
static inline bool is_tcf_skbedit_with_flag(const struct tc_action *a, u32 flag)
{
#ifdef CONFIG_NET_CLS_ACT
	u32 flags;

	if (a->ops && a->ops->id == TCA_ID_SKBEDIT) {
		rcu_read_lock();
		flags = rcu_dereference(to_skbedit(a)->params)->flags;
		rcu_read_unlock();
		return flags == flag;
	}
#endif
	return false;
}

/* Return true iff action is mark */
static inline bool is_tcf_skbedit_mark(const struct tc_action *a)
{
	return is_tcf_skbedit_with_flag(a, SKBEDIT_F_MARK);
}

static inline u32 tcf_skbedit_mark(const struct tc_action *a)
{
	u32 mark;

	rcu_read_lock();
	mark = rcu_dereference(to_skbedit(a)->params)->mark;
	rcu_read_unlock();

	return mark;
}

/* Return true iff action is ptype */
static inline bool is_tcf_skbedit_ptype(const struct tc_action *a)
{
	return is_tcf_skbedit_with_flag(a, SKBEDIT_F_PTYPE);
}

static inline u32 tcf_skbedit_ptype(const struct tc_action *a)
{
	u16 ptype;

	rcu_read_lock();
	ptype = rcu_dereference(to_skbedit(a)->params)->ptype;
	rcu_read_unlock();

	return ptype;
}

/* Return true iff action is priority */
static inline bool is_tcf_skbedit_priority(const struct tc_action *a)
{
	return is_tcf_skbedit_with_flag(a, SKBEDIT_F_PRIORITY);
}

static inline u32 tcf_skbedit_priority(const struct tc_action *a)
{
	u32 priority;

	rcu_read_lock();
	priority = rcu_dereference(to_skbedit(a)->params)->priority;
	rcu_read_unlock();

	return priority;
}

#endif /* __NET_TC_SKBEDIT_H */
