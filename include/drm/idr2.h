/*
 * include/linux/idr.h
 * 
 * 2002-10-18  written by Jim Houston jim.houston@ccur.com
 *	Copyright (C) 2002 by Concurrent Computer Corporation
 *	Distributed under the GNU GPL license version 2.
 *
 * Small id to pointer translation service avoiding fixed sized
 * tables.
 */

#ifndef __IDR2_H__
#define __IDR2_H__

#include <linux/types.h>
#include <linux/bitops.h>
#include <linux/init.h>
#include <linux/rcupdate.h>

/*
 * We want shallower trees and thus more bits covered at each layer.  8
 * bits gives us large enough first layer for most use cases and maximum
 * tree depth of 4.  Each idr2_layer is slightly larger than 2k on 64bit and
 * 1k on 32bit.
 */
#define IDR2_BITS 8
#define IDR2_SIZE (1 << IDR2_BITS)
#define IDR2_MASK ((1 << IDR2_BITS)-1)

struct idr2_layer {
	int			prefix;	/* the ID prefix of this idr2_layer */
	int			layer;	/* distance from leaf */
	struct idr2_layer __rcu	*ary[1<<IDR2_BITS];
	int			count;	/* When zero, we can release it */
	union {
		/* A zero bit means "space here" */
		DECLARE_BITMAP(bitmap, IDR2_SIZE);
		struct rcu_head		rcu_head;
	};
};

struct idr2 {
	struct idr2_layer __rcu	*hint;	/* the last layer allocated from */
	struct idr2_layer __rcu	*top;
	int			layers;	/* only valid w/o concurrent changes */
	int			cur;	/* current pos for cyclic allocation */
	spinlock_t		lock;
	int			id_free_cnt;
	struct idr2_layer	*id_free;
};

#define IDR2_INIT(name)							\
{									\
	.lock			= __SPIN_LOCK_UNLOCKED(name.lock),	\
}
#define DEFINE_IDR2(name)	struct idr2 name = IDR2_INIT(name)

/**
 * DOC: idr2 sync
 * idr2 synchronization (stolen from radix-tree.h)
 *
 * idr2_find() is able to be called locklessly, using RCU. The caller must
 * ensure calls to this function are made within rcu_read_lock() regions.
 * Other readers (lock-free or otherwise) and modifications may be running
 * concurrently.
 *
 * It is still required that the caller manage the synchronization and
 * lifetimes of the items. So if RCU lock-free lookups are used, typically
 * this would mean that the items have their own locks, or are amenable to
 * lock-free access; and that the items are freed by RCU (or only freed after
 * having been deleted from the idr2 tree *and* a synchronize_rcu() grace
 * period).
 */

/*
 * This is what we export.
 */

void *idr2_find_slowpath(struct idr2 *idp, int id);
void idr2_preload(gfp_t gfp_mask);
int idr2_alloc(struct idr2 *idp, void *ptr, int start, int end, gfp_t gfp_mask);
int idr2_alloc_cyclic(struct idr2 *idr2, void *ptr, int start, int end, gfp_t gfp_mask);
int idr2_for_each(struct idr2 *idp,
		 int (*fn)(int id, void *p, void *data), void *data);
void *idr2_get_next(struct idr2 *idp, int *nextid);
void *idr2_replace(struct idr2 *idp, void *ptr, int id);
void idr2_remove(struct idr2 *idp, int id);
void idr2_destroy(struct idr2 *idp);
void idr2_init(struct idr2 *idp);
bool idr2_is_empty(struct idr2 *idp);

/**
 * idr2_preload_end - end preload section started with idr2_preload()
 *
 * Each idr2_preload() should be matched with an invocation of this
 * function.  See idr2_preload() for details.
 */
static inline void idr2_preload_end(void)
{
	preempt_enable();
}

/**
 * idr2_find - return pointer for given id
 * @idr2: idr2 handle
 * @id: lookup key
 *
 * Return the pointer given the id it has been registered with.  A %NULL
 * return indicates that @id is not valid or you passed %NULL in
 * idr2_get_new().
 *
 * This function can be called under rcu_read_lock(), given that the leaf
 * pointers lifetimes are correctly managed.
 */
static inline void *idr2_find(struct idr2 *idr2, int id)
{
	struct idr2_layer *hint = rcu_dereference_raw(idr2->hint);

	if (hint && (id & ~IDR2_MASK) == hint->prefix)
		return rcu_dereference_raw(hint->ary[id & IDR2_MASK]);

	return idr2_find_slowpath(idr2, id);
}

/**
 * idr2_for_each_entry - iterate over an idr2's elements of a given type
 * @idp:     idr2 handle
 * @entry:   the type * to use as cursor
 * @id:      id entry's key
 *
 * @entry and @id do not need to be initialized before the loop, and
 * after normal terminatinon @entry is left with the value NULL.  This
 * is convenient for a "not found" value.
 */
#define idr2_for_each_entry(idp, entry, id)			\
	for (id = 0; ((entry) = idr2_get_next(idp, &(id))) != NULL; ++id)

/*
 * IDA2 - IDR2 based id allocator, use when translation from id to
 * pointer isn't necessary.
 *
 * IDA2_BITMAP_LONGS is calculated to be one less to accommodate
 * ida2_bitmap->nr_busy so that the whole struct fits in 128 bytes.
 */
#define IDA2_CHUNK_SIZE		128	/* 128 bytes per chunk */
#define IDA2_BITMAP_LONGS	(IDA2_CHUNK_SIZE / sizeof(long) - 1)
#define IDA2_BITMAP_BITS 	(IDA2_BITMAP_LONGS * sizeof(long) * 8)

struct ida2_bitmap {
	long			nr_busy;
	unsigned long		bitmap[IDA2_BITMAP_LONGS];
};

struct ida2 {
	struct idr2		idr2;
	struct ida2_bitmap	*free_bitmap;
};

#define IDA2_INIT(name)		{ .idr2 = IDR2_INIT((name).idr2), .free_bitmap = NULL, }
#define DEFINE_IDA2(name)	struct ida2 name = IDA2_INIT(name)

int ida2_pre_get(struct ida2 *ida2, gfp_t gfp_mask);
int ida2_get_new_above(struct ida2 *ida2, int starting_id, int *p_id);
void ida2_remove(struct ida2 *ida2, int id);
void ida2_destroy(struct ida2 *ida2);
void ida2_init(struct ida2 *ida2);

int ida2_simple_get(struct ida2 *ida2, unsigned int start, unsigned int end,
		   gfp_t gfp_mask);
void ida2_simple_remove(struct ida2 *ida2, unsigned int id);

/**
 * ida2_get_new - allocate new ID
 * @ida2:	idr2 handle
 * @p_id:	pointer to the allocated handle
 *
 * Simple wrapper around ida2_get_new_above() w/ @starting_id of zero.
 */
static inline int ida2_get_new(struct ida2 *ida2, int *p_id)
{
	return ida2_get_new_above(ida2, 0, p_id);
}

void __init idr2_init_cache(void);

#endif /* __IDR2_H__ */
