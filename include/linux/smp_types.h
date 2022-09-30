/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __LINUX_SMP_TYPES_H
#define __LINUX_SMP_TYPES_H

#include <linux/llist.h>

enum {
	CSD_FLAG_LOCK		= 0x01,

	IRQ_WORK_PENDING	= 0x01,
	IRQ_WORK_BUSY		= 0x02,
	IRQ_WORK_LAZY		= 0x04, /* No IPI, wait for tick */
	IRQ_WORK_HARD_IRQ	= 0x08, /* IRQ context on PREEMPT_RT */

	IRQ_WORK_CLAIMED	= (IRQ_WORK_PENDING | IRQ_WORK_BUSY),

	CSD_TYPE_ASYNC		= 0x00,
	CSD_TYPE_SYNC		= 0x10,
	CSD_TYPE_IRQ_WORK	= 0x20,
	CSD_TYPE_TTWU		= 0x30,

	CSD_FLAG_TYPE_MASK	= 0xF0,
};

/*
 * struct __call_single_node is the primary type on
 * smp.c:call_single_queue.
 *
 * flush_smp_call_function_queue() only reads the type from
 * __call_single_node::u_flags as a regular load, the above
 * (anonymous) enum defines all the bits of this word.
 *
 * Other bits are not modified until the type is known.
 *
 * CSD_TYPE_SYNC/ASYNC:
 *	struct {
 *		unsigned int flags;
 *		struct llist_node node;
 *		smp_call_func_t func;
 *		void *info;
 *	};
 *
 * CSD_TYPE_IRQ_WORK:
 *	struct {
 *		atomic_t flags;
 *		struct llist_node node;
 *		void (*func)(struct irq_work *);
 *	};
 *
 * CSD_TYPE_TTWU:
 *	struct {
 *		unsigned int flags;
 *		struct llist_node node;
 *	};
 *
 */

struct __call_single_node {
	union {
		unsigned int	u_flags;
		atomic_t	a_flags;
	};
	struct llist_node	llist;
};

#endif /* __LINUX_SMP_TYPES_H */
