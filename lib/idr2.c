/*
 * 2002-10-18  written by Jim Houston jim.houston@ccur.com
 *	Copyright (C) 2002 by Concurrent Computer Corporation
 *	Distributed under the GNU GPL license version 2.
 *
 * Modified by George Anzinger to reuse immediately and to use
 * find bit instructions.  Also removed _irq on spinlocks.
 *
 * Modified by Nadia Derbey to make it RCU safe.
 *
 * Small id to pointer translation service.
 *
 * It uses a radix tree like structure as a sparse array indexed
 * by the id to obtain the pointer.  The bitmap makes allocating
 * a new id quick.
 *
 * You call it to allocate an id (an int) an associate with that id a
 * pointer or what ever, we treat it as a (void *).  You can pass this
 * id to a user for him to pass back at a later time.  You then pass
 * that id to this code and it returns your pointer.
 */

#ifndef TEST                        // to test in user space...
#include <linux/slab.h>
#include <linux/init.h>
#include <linux/export.h>
#endif
#include <linux/err.h>
#include <linux/string.h>
#include <linux/idr2.h>
#include <linux/spinlock.h>
#include <linux/percpu.h>
#include <linux/hardirq.h>

#define MAX_IDR2_SHIFT		(sizeof(int) * 8 - 1)
#define MAX_IDR2_BIT		(1U << MAX_IDR2_SHIFT)

/* Leave the possibility of an incomplete final layer */
#define MAX_IDR2_LEVEL ((MAX_IDR2_SHIFT + IDR2_BITS - 1) / IDR2_BITS)

/* Number of id_layer structs to leave in free list */
#define MAX_IDR2_FREE (MAX_IDR2_LEVEL * 2)

static struct kmem_cache *idr2_layer_cache;
static DEFINE_PER_CPU(struct idr2_layer *, idr2_preload_head);
static DEFINE_PER_CPU(int, idr2_preload_cnt);
static DEFINE_SPINLOCK(simple_ida2_lock);

/* the maximum ID which can be allocated given idr2->layers */
static int idr2_max(int layers)
{
	int bits = min_t(int, layers * IDR2_BITS, MAX_IDR2_SHIFT);

	return (1 << bits) - 1;
}

/*
 * Prefix mask for an idr2_layer at @layer.  For layer 0, the prefix mask is
 * all bits except for the lower IDR2_BITS.  For layer 1, 2 * IDR2_BITS, and
 * so on.
 */
static int idr2_layer_prefix_mask(int layer)
{
	return ~idr2_max(layer + 1);
}

static struct idr2_layer *get_from_free_list(struct idr2 *idp)
{
	struct idr2_layer *p;
	unsigned long flags;

	spin_lock_irqsave(&idp->lock, flags);
	if ((p = idp->id_free)) {
		idp->id_free = p->ary[0];
		idp->id_free_cnt--;
		p->ary[0] = NULL;
	}
	spin_unlock_irqrestore(&idp->lock, flags);
	return(p);
}

/**
 * idr2_layer_alloc - allocate a new idr2_layer
 * @gfp_mask: allocation mask
 * @layer_idr2: optional idr2 to allocate from
 *
 * If @layer_idr2 is %NULL, directly allocate one using @gfp_mask or fetch
 * one from the per-cpu preload buffer.  If @layer_idr2 is not %NULL, fetch
 * an idr2_layer from @idr2->id_free.
 *
 * @layer_idr2 is to maintain backward compatibility with the old alloc
 * interface - idr2_pre_get() and idr2_get_new*() - and will be removed
 * together with per-pool preload buffer.
 */
static struct idr2_layer *idr2_layer_alloc(gfp_t gfp_mask, struct idr2 *layer_idr2)
{
	struct idr2_layer *new;

	/* this is the old path, bypass to get_from_free_list() */
	if (layer_idr2)
		return get_from_free_list(layer_idr2);

	/*
	 * Try to allocate directly from kmem_cache.  We want to try this
	 * before preload buffer; otherwise, non-preloading idr2_alloc()
	 * users will end up taking advantage of preloading ones.  As the
	 * following is allowed to fail for preloaded cases, suppress
	 * warning this time.
	 */
	new = kmem_cache_zalloc(idr2_layer_cache, gfp_mask | __GFP_NOWARN);
	if (new)
		return new;

	/*
	 * Try to fetch one from the per-cpu preload buffer if in process
	 * context.  See idr2_preload() for details.
	 */
	if (!in_interrupt()) {
		preempt_disable();
		new = __get_cpu_var(idr2_preload_head);
		if (new) {
			__get_cpu_var(idr2_preload_head) = new->ary[0];
			__get_cpu_var(idr2_preload_cnt)--;
			new->ary[0] = NULL;
		}
		preempt_enable();
		if (new)
			return new;
	}

	/*
	 * Both failed.  Try kmem_cache again w/o adding __GFP_NOWARN so
	 * that memory allocation failure warning is printed as intended.
	 */
	return kmem_cache_zalloc(idr2_layer_cache, gfp_mask);
}

static void idr2_layer_rcu_free(struct rcu_head *head)
{
	struct idr2_layer *layer;

	layer = container_of(head, struct idr2_layer, rcu_head);
	kmem_cache_free(idr2_layer_cache, layer);
}

static inline void free_layer(struct idr2 *idr2, struct idr2_layer *p)
{
	if (idr2->hint == p)
		RCU_INIT_POINTER(idr2->hint, NULL);
	call_rcu(&p->rcu_head, idr2_layer_rcu_free);
}

/* only called when idp->lock is held */
static void __move_to_free_list(struct idr2 *idp, struct idr2_layer *p)
{
	p->ary[0] = idp->id_free;
	idp->id_free = p;
	idp->id_free_cnt++;
}

static void move_to_free_list(struct idr2 *idp, struct idr2_layer *p)
{
	unsigned long flags;

	/*
	 * Depends on the return element being zeroed.
	 */
	spin_lock_irqsave(&idp->lock, flags);
	__move_to_free_list(idp, p);
	spin_unlock_irqrestore(&idp->lock, flags);
}

static void idr2_mark_full(struct idr2_layer **pa, int id)
{
	struct idr2_layer *p = pa[0];
	int l = 0;

	__set_bit(id & IDR2_MASK, p->bitmap);
	/*
	 * If this layer is full mark the bit in the layer above to
	 * show that this part of the radix tree is full.  This may
	 * complete the layer above and require walking up the radix
	 * tree.
	 */
	while (bitmap_full(p->bitmap, IDR2_SIZE)) {
		if (!(p = pa[++l]))
			break;
		id = id >> IDR2_BITS;
		__set_bit((id & IDR2_MASK), p->bitmap);
	}
}

static int __idr2_pre_get(struct idr2 *idp, gfp_t gfp_mask)
{
	while (idp->id_free_cnt < MAX_IDR2_FREE) {
		struct idr2_layer *new;
		new = kmem_cache_zalloc(idr2_layer_cache, gfp_mask);
		if (new == NULL)
			return (0);
		move_to_free_list(idp, new);
	}
	return 1;
}

/**
 * sub_alloc - try to allocate an id without growing the tree depth
 * @idp: idr2 handle
 * @starting_id: id to start search at
 * @pa: idr2_layer[MAX_IDR2_LEVEL] used as backtrack buffer
 * @gfp_mask: allocation mask for idr2_layer_alloc()
 * @layer_idr2: optional idr2 passed to idr2_layer_alloc()
 *
 * Allocate an id in range [@starting_id, INT_MAX] from @idp without
 * growing its depth.  Returns
 *
 *  the allocated id >= 0 if successful,
 *  -EAGAIN if the tree needs to grow for allocation to succeed,
 *  -ENOSPC if the id space is exhausted,
 *  -ENOMEM if more idr2_layers need to be allocated.
 */
static int sub_alloc(struct idr2 *idp, int *starting_id, struct idr2_layer **pa,
		     gfp_t gfp_mask, struct idr2 *layer_idr2)
{
	int n, m, sh;
	struct idr2_layer *p, *new;
	int l, id, oid;

	id = *starting_id;
 restart:
	p = idp->top;
	l = idp->layers;
	pa[l--] = NULL;
	while (1) {
		/*
		 * We run around this while until we reach the leaf node...
		 */
		n = (id >> (IDR2_BITS*l)) & IDR2_MASK;
		m = find_next_zero_bit(p->bitmap, IDR2_SIZE, n);
		if (m == IDR2_SIZE) {
			/* no space available go back to previous layer. */
			l++;
			oid = id;
			id = (id | ((1 << (IDR2_BITS * l)) - 1)) + 1;

			/* if already at the top layer, we need to grow */
			if (id > idr2_max(idp->layers)) {
				*starting_id = id;
				return -EAGAIN;
			}
			p = pa[l];
			BUG_ON(!p);

			/* If we need to go up one layer, continue the
			 * loop; otherwise, restart from the top.
			 */
			sh = IDR2_BITS * (l + 1);
			if (oid >> sh == id >> sh)
				continue;
			else
				goto restart;
		}
		if (m != n) {
			sh = IDR2_BITS*l;
			id = ((id >> sh) ^ n ^ m) << sh;
		}
		if ((id >= MAX_IDR2_BIT) || (id < 0))
			return -ENOSPC;
		if (l == 0)
			break;
		/*
		 * Create the layer below if it is missing.
		 */
		if (!p->ary[m]) {
			new = idr2_layer_alloc(gfp_mask, layer_idr2);
			if (!new)
				return -ENOMEM;
			new->layer = l-1;
			new->prefix = id & idr2_layer_prefix_mask(new->layer);
			rcu_assign_pointer(p->ary[m], new);
			p->count++;
		}
		pa[l--] = p;
		p = p->ary[m];
	}

	pa[l] = p;
	return id;
}

static int idr2_get_empty_slot(struct idr2 *idp, int starting_id,
			      struct idr2_layer **pa, gfp_t gfp_mask,
			      struct idr2 *layer_idr2)
{
	struct idr2_layer *p, *new;
	int layers, v, id;
	unsigned long flags;

	id = starting_id;
build_up:
	p = idp->top;
	layers = idp->layers;
	if (unlikely(!p)) {
		if (!(p = idr2_layer_alloc(gfp_mask, layer_idr2)))
			return -ENOMEM;
		p->layer = 0;
		layers = 1;
	}
	/*
	 * Add a new layer to the top of the tree if the requested
	 * id is larger than the currently allocated space.
	 */
	while (id > idr2_max(layers)) {
		layers++;
		if (!p->count) {
			/* special case: if the tree is currently empty,
			 * then we grow the tree by moving the top node
			 * upwards.
			 */
			p->layer++;
			WARN_ON_ONCE(p->prefix);
			continue;
		}
		if (!(new = idr2_layer_alloc(gfp_mask, layer_idr2))) {
			/*
			 * The allocation failed.  If we built part of
			 * the structure tear it down.
			 */
			spin_lock_irqsave(&idp->lock, flags);
			for (new = p; p && p != idp->top; new = p) {
				p = p->ary[0];
				new->ary[0] = NULL;
				new->count = 0;
				bitmap_clear(new->bitmap, 0, IDR2_SIZE);
				__move_to_free_list(idp, new);
			}
			spin_unlock_irqrestore(&idp->lock, flags);
			return -ENOMEM;
		}
		new->ary[0] = p;
		new->count = 1;
		new->layer = layers-1;
		new->prefix = id & idr2_layer_prefix_mask(new->layer);
		if (bitmap_full(p->bitmap, IDR2_SIZE))
			__set_bit(0, new->bitmap);
		p = new;
	}
	rcu_assign_pointer(idp->top, p);
	idp->layers = layers;
	v = sub_alloc(idp, &id, pa, gfp_mask, layer_idr2);
	if (v == -EAGAIN)
		goto build_up;
	return(v);
}

/*
 * @id and @pa are from a successful allocation from idr2_get_empty_slot().
 * Install the user pointer @ptr and mark the slot full.
 */
static void idr2_fill_slot(struct idr2 *idr2, void *ptr, int id,
			  struct idr2_layer **pa)
{
	/* update hint used for lookup, cleared from free_layer() */
	rcu_assign_pointer(idr2->hint, pa[0]);

	rcu_assign_pointer(pa[0]->ary[id & IDR2_MASK], (struct idr2_layer *)ptr);
	pa[0]->count++;
	idr2_mark_full(pa, id);
}


/**
 * idr2_preload - preload for idr2_alloc()
 * @gfp_mask: allocation mask to use for preloading
 *
 * Preload per-cpu layer buffer for idr2_alloc().  Can only be used from
 * process context and each idr2_preload() invocation should be matched with
 * idr2_preload_end().  Note that preemption is disabled while preloaded.
 *
 * The first idr2_alloc() in the preloaded section can be treated as if it
 * were invoked with @gfp_mask used for preloading.  This allows using more
 * permissive allocation masks for idr2s protected by spinlocks.
 *
 * For example, if idr2_alloc() below fails, the failure can be treated as
 * if idr2_alloc() were called with GFP_KERNEL rather than GFP_NOWAIT.
 *
 *	idr2_preload(GFP_KERNEL);
 *	spin_lock(lock);
 *
 *	id = idr2_alloc(idr2, ptr, start, end, GFP_NOWAIT);
 *
 *	spin_unlock(lock);
 *	idr2_preload_end();
 *	if (id < 0)
 *		error;
 */
void idr2_preload(gfp_t gfp_mask)
{
	/*
	 * Consuming preload buffer from non-process context breaks preload
	 * allocation guarantee.  Disallow usage from those contexts.
	 */
	WARN_ON_ONCE(in_interrupt());
	might_sleep_if(gfp_mask & __GFP_WAIT);

	preempt_disable();

	/*
	 * idr2_alloc() is likely to succeed w/o full idr2_layer buffer and
	 * return value from idr2_alloc() needs to be checked for failure
	 * anyway.  Silently give up if allocation fails.  The caller can
	 * treat failures from idr2_alloc() as if idr2_alloc() were called
	 * with @gfp_mask which should be enough.
	 */
	while (__get_cpu_var(idr2_preload_cnt) < MAX_IDR2_FREE) {
		struct idr2_layer *new;

		preempt_enable();
		new = kmem_cache_zalloc(idr2_layer_cache, gfp_mask);
		preempt_disable();
		if (!new)
			break;

		/* link the new one to per-cpu preload list */
		new->ary[0] = __get_cpu_var(idr2_preload_head);
		__get_cpu_var(idr2_preload_head) = new;
		__get_cpu_var(idr2_preload_cnt)++;
	}
}
EXPORT_SYMBOL(idr2_preload);

/**
 * idr2_alloc - allocate new idr2 entry
 * @idr2: the (initialized) idr2
 * @ptr: pointer to be associated with the new id
 * @start: the minimum id (inclusive)
 * @end: the maximum id (exclusive, <= 0 for max)
 * @gfp_mask: memory allocation flags
 *
 * Allocate an id in [start, end) and associate it with @ptr.  If no ID is
 * available in the specified range, returns -ENOSPC.  On memory allocation
 * failure, returns -ENOMEM.
 *
 * Note that @end is treated as max when <= 0.  This is to always allow
 * using @start + N as @end as long as N is inside integer range.
 *
 * The user is responsible for exclusively synchronizing all operations
 * which may modify @idr2.  However, read-only accesses such as idr2_find()
 * or iteration can be performed under RCU read lock provided the user
 * destroys @ptr in RCU-safe way after removal from idr2.
 */
int idr2_alloc(struct idr2 *idr2, void *ptr, int start, int end, gfp_t gfp_mask)
{
	int max = end > 0 ? end - 1 : INT_MAX;	/* inclusive upper limit */
	struct idr2_layer *pa[MAX_IDR2_LEVEL + 1];
	int id;

	might_sleep_if(gfp_mask & __GFP_WAIT);

	/* sanity checks */
	if (WARN_ON_ONCE(start < 0))
		return -EINVAL;
	if (unlikely(max < start))
		return -ENOSPC;

	/* allocate id */
	id = idr2_get_empty_slot(idr2, start, pa, gfp_mask, NULL);
	if (unlikely(id < 0))
		return id;
	if (unlikely(id > max))
		return -ENOSPC;

	idr2_fill_slot(idr2, ptr, id, pa);
	return id;
}
EXPORT_SYMBOL_GPL(idr2_alloc);

/**
 * idr2_alloc_cyclic - allocate new idr2 entry in a cyclical fashion
 * @idr2: the (initialized) idr2
 * @ptr: pointer to be associated with the new id
 * @start: the minimum id (inclusive)
 * @end: the maximum id (exclusive, <= 0 for max)
 * @gfp_mask: memory allocation flags
 *
 * Essentially the same as idr2_alloc, but prefers to allocate progressively
 * higher ids if it can. If the "cur" counter wraps, then it will start again
 * at the "start" end of the range and allocate one that has already been used.
 */
int idr2_alloc_cyclic(struct idr2 *idr2, void *ptr, int start, int end,
			gfp_t gfp_mask)
{
	int id;

	id = idr2_alloc(idr2, ptr, max(start, idr2->cur), end, gfp_mask);
	if (id == -ENOSPC)
		id = idr2_alloc(idr2, ptr, start, end, gfp_mask);

	if (likely(id >= 0))
		idr2->cur = id + 1;
	return id;
}
EXPORT_SYMBOL(idr2_alloc_cyclic);

static void idr2_remove_warning(int id)
{
	WARN(1, "idr2_remove called for id=%d which is not allocated.\n", id);
}

static void sub_remove(struct idr2 *idp, int shift, int id)
{
	struct idr2_layer *p = idp->top;
	struct idr2_layer **pa[MAX_IDR2_LEVEL + 1];
	struct idr2_layer ***paa = &pa[0];
	struct idr2_layer *to_free;
	int n;

	*paa = NULL;
	*++paa = &idp->top;

	while ((shift > 0) && p) {
		n = (id >> shift) & IDR2_MASK;
		__clear_bit(n, p->bitmap);
		*++paa = &p->ary[n];
		p = p->ary[n];
		shift -= IDR2_BITS;
	}
	n = id & IDR2_MASK;
	if (likely(p != NULL && test_bit(n, p->bitmap))) {
		__clear_bit(n, p->bitmap);
		RCU_INIT_POINTER(p->ary[n], NULL);
		to_free = NULL;
		while(*paa && ! --((**paa)->count)){
			if (to_free)
				free_layer(idp, to_free);
			to_free = **paa;
			**paa-- = NULL;
		}
		if (!*paa)
			idp->layers = 0;
		if (to_free)
			free_layer(idp, to_free);
	} else
		idr2_remove_warning(id);
}

/**
 * idr2_remove - remove the given id and free its slot
 * @idp: idr2 handle
 * @id: unique key
 */
void idr2_remove(struct idr2 *idp, int id)
{
	struct idr2_layer *p;
	struct idr2_layer *to_free;

	if (id < 0)
		return;

	if (id > idr2_max(idp->layers)) {
		idr2_remove_warning(id);
		return;
	}

	sub_remove(idp, (idp->layers - 1) * IDR2_BITS, id);
	if (idp->top && idp->top->count == 1 && (idp->layers > 1) &&
	    idp->top->ary[0]) {
		/*
		 * Single child at leftmost slot: we can shrink the tree.
		 * This level is not needed anymore since when layers are
		 * inserted, they are inserted at the top of the existing
		 * tree.
		 */
		to_free = idp->top;
		p = idp->top->ary[0];
		rcu_assign_pointer(idp->top, p);
		--idp->layers;
		to_free->count = 0;
		bitmap_clear(to_free->bitmap, 0, IDR2_SIZE);
		free_layer(idp, to_free);
	}
}
EXPORT_SYMBOL(idr2_remove);

static void __idr2_remove_all(struct idr2 *idp)
{
	int n, id, max;
	int bt_mask;
	struct idr2_layer *p;
	struct idr2_layer *pa[MAX_IDR2_LEVEL + 1];
	struct idr2_layer **paa = &pa[0];

	n = idp->layers * IDR2_BITS;
	*paa = idp->top;
	RCU_INIT_POINTER(idp->top, NULL);
	max = idr2_max(idp->layers);

	id = 0;
	while (id >= 0 && id <= max) {
		p = *paa;
		while (n > IDR2_BITS && p) {
			n -= IDR2_BITS;
			p = p->ary[(id >> n) & IDR2_MASK];
			*++paa = p;
		}

		bt_mask = id;
		id += 1 << n;
		/* Get the highest bit that the above add changed from 0->1. */
		while (n < fls(id ^ bt_mask)) {
			if (*paa)
				free_layer(idp, *paa);
			n += IDR2_BITS;
			--paa;
		}
	}
	idp->layers = 0;
}

/**
 * idr2_destroy - release all cached layers within an idr2 tree
 * @idp: idr2 handle
 *
 * Free all id mappings and all idp_layers.  After this function, @idp is
 * completely unused and can be freed / recycled.  The caller is
 * responsible for ensuring that no one else accesses @idp during or after
 * idr2_destroy().
 *
 * A typical clean-up sequence for objects stored in an idr2 tree will use
 * idr2_for_each() to free all objects, if necessary, then idr2_destroy() to
 * free up the id mappings and cached idr2_layers.
 */
void idr2_destroy(struct idr2 *idp)
{
	__idr2_remove_all(idp);

	while (idp->id_free_cnt) {
		struct idr2_layer *p = get_from_free_list(idp);
		kmem_cache_free(idr2_layer_cache, p);
	}
}
EXPORT_SYMBOL(idr2_destroy);

void *idr2_find_slowpath(struct idr2 *idp, int id)
{
	int n;
	struct idr2_layer *p;

	if (id < 0)
		return NULL;

	p = rcu_dereference_raw(idp->top);
	if (!p)
		return NULL;
	n = (p->layer+1) * IDR2_BITS;

	if (id > idr2_max(p->layer + 1))
		return NULL;
	BUG_ON(n == 0);

	while (n > 0 && p) {
		n -= IDR2_BITS;
		BUG_ON(n != p->layer*IDR2_BITS);
		p = rcu_dereference_raw(p->ary[(id >> n) & IDR2_MASK]);
	}
	return((void *)p);
}
EXPORT_SYMBOL(idr2_find_slowpath);

/**
 * idr2_for_each - iterate through all stored pointers
 * @idp: idr2 handle
 * @fn: function to be called for each pointer
 * @data: data passed back to callback function
 *
 * Iterate over the pointers registered with the given idr2.  The
 * callback function will be called for each pointer currently
 * registered, passing the id, the pointer and the data pointer passed
 * to this function.  It is not safe to modify the idr2 tree while in
 * the callback, so functions such as idr2_get_new and idr2_remove are
 * not allowed.
 *
 * We check the return of @fn each time. If it returns anything other
 * than %0, we break out and return that value.
 *
 * The caller must serialize idr2_for_each() vs idr2_get_new() and idr2_remove().
 */
int idr2_for_each(struct idr2 *idp,
		 int (*fn)(int id, void *p, void *data), void *data)
{
	int n, id, max, error = 0;
	struct idr2_layer *p;
	struct idr2_layer *pa[MAX_IDR2_LEVEL + 1];
	struct idr2_layer **paa = &pa[0];

	n = idp->layers * IDR2_BITS;
	*paa = rcu_dereference_raw(idp->top);
	max = idr2_max(idp->layers);

	id = 0;
	while (id >= 0 && id <= max) {
		p = *paa;
		while (n > 0 && p) {
			n -= IDR2_BITS;
			p = rcu_dereference_raw(p->ary[(id >> n) & IDR2_MASK]);
			*++paa = p;
		}

		if (p) {
			error = fn(id, (void *)p, data);
			if (error)
				break;
		}

		id += 1 << n;
		while (n < fls(id)) {
			n += IDR2_BITS;
			--paa;
		}
	}

	return error;
}
EXPORT_SYMBOL(idr2_for_each);

/**
 * idr2_get_next - lookup next object of id to given id.
 * @idp: idr2 handle
 * @nextidp:  pointer to lookup key
 *
 * Returns pointer to registered object with id, which is next number to
 * given id. After being looked up, *@nextidp will be updated for the next
 * iteration.
 *
 * This function can be called under rcu_read_lock(), given that the leaf
 * pointers lifetimes are correctly managed.
 */
void *idr2_get_next(struct idr2 *idp, int *nextidp)
{
	struct idr2_layer *p, *pa[MAX_IDR2_LEVEL + 1];
	struct idr2_layer **paa = &pa[0];
	int id = *nextidp;
	int n, max;

	/* find first ent */
	p = *paa = rcu_dereference_raw(idp->top);
	if (!p)
		return NULL;
	n = (p->layer + 1) * IDR2_BITS;
	max = idr2_max(p->layer + 1);

	while (id >= 0 && id <= max) {
		p = *paa;
		while (n > 0 && p) {
			n -= IDR2_BITS;
			p = rcu_dereference_raw(p->ary[(id >> n) & IDR2_MASK]);
			*++paa = p;
		}

		if (p) {
			*nextidp = id;
			return p;
		}

		/*
		 * Proceed to the next layer at the current level.  Unlike
		 * idr2_for_each(), @id isn't guaranteed to be aligned to
		 * layer boundary at this point and adding 1 << n may
		 * incorrectly skip IDs.  Make sure we jump to the
		 * beginning of the next layer using round_up().
		 */
		id = round_up(id + 1, 1 << n);
		while (n < fls(id)) {
			n += IDR2_BITS;
			--paa;
		}
	}
	return NULL;
}
EXPORT_SYMBOL(idr2_get_next);


/**
 * idr2_replace - replace pointer for given id
 * @idp: idr2 handle
 * @ptr: pointer you want associated with the id
 * @id: lookup key
 *
 * Replace the pointer registered with an id and return the old value.
 * A %-ENOENT return indicates that @id was not found.
 * A %-EINVAL return indicates that @id was not within valid constraints.
 *
 * The caller must serialize with writers.
 */
void *idr2_replace(struct idr2 *idp, void *ptr, int id)
{
	int n;
	struct idr2_layer *p, *old_p;

	if (id < 0)
		return ERR_PTR(-EINVAL);

	p = idp->top;
	if (!p)
		return ERR_PTR(-ENOENT);

	if (id > idr2_max(p->layer + 1))
		return ERR_PTR(-ENOENT);

	n = p->layer * IDR2_BITS;
	while ((n > 0) && p) {
		p = p->ary[(id >> n) & IDR2_MASK];
		n -= IDR2_BITS;
	}

	n = id & IDR2_MASK;
	if (unlikely(p == NULL || !test_bit(n, p->bitmap)))
		return ERR_PTR(-ENOENT);

	old_p = p->ary[n];
	rcu_assign_pointer(p->ary[n], ptr);

	return old_p;
}
EXPORT_SYMBOL(idr2_replace);

void __init idr2_init_cache(void)
{
	idr2_layer_cache = kmem_cache_create("idr2_layer_cache",
				sizeof(struct idr2_layer), 0, SLAB_PANIC, NULL);
}

/**
 * idr2_init - initialize idr2 handle
 * @idp:	idr2 handle
 *
 * This function is use to set up the handle (@idp) that you will pass
 * to the rest of the functions.
 */
void idr2_init(struct idr2 *idp)
{
	memset(idp, 0, sizeof(struct idr2));
	spin_lock_init(&idp->lock);
}
EXPORT_SYMBOL(idr2_init);

static int idr2_has_entry(int id, void *p, void *data)
{
	return 1;
}

bool idr2_is_empty(struct idr2 *idp)
{
	return !idr2_for_each(idp, idr2_has_entry, NULL);
}
EXPORT_SYMBOL(idr2_is_empty);

/**
 * DOC: IDA2 description
 * IDA2 - IDR2 based ID allocator
 *
 * This is id allocator without id -> pointer translation.  Memory
 * usage is much lower than full blown idr2 because each id only
 * occupies a bit.  ida2 uses a custom leaf node which contains
 * IDA2_BITMAP_BITS slots.
 *
 * 2007-04-25  written by Tejun Heo <htejun@gmail.com>
 */

static void free_bitmap(struct ida2 *ida2, struct ida2_bitmap *bitmap)
{
	unsigned long flags;

	if (!ida2->free_bitmap) {
		spin_lock_irqsave(&ida2->idr2.lock, flags);
		if (!ida2->free_bitmap) {
			ida2->free_bitmap = bitmap;
			bitmap = NULL;
		}
		spin_unlock_irqrestore(&ida2->idr2.lock, flags);
	}

	kfree(bitmap);
}

/**
 * ida2_pre_get - reserve resources for ida2 allocation
 * @ida2:	ida2 handle
 * @gfp_mask:	memory allocation flag
 *
 * This function should be called prior to locking and calling the
 * following function.  It preallocates enough memory to satisfy the
 * worst possible allocation.
 *
 * If the system is REALLY out of memory this function returns %0,
 * otherwise %1.
 */
int ida2_pre_get(struct ida2 *ida2, gfp_t gfp_mask)
{
	/* allocate idr2_layers */
	if (!__idr2_pre_get(&ida2->idr2, gfp_mask))
		return 0;

	/* allocate free_bitmap */
	if (!ida2->free_bitmap) {
		struct ida2_bitmap *bitmap;

		bitmap = kmalloc(sizeof(struct ida2_bitmap), gfp_mask);
		if (!bitmap)
			return 0;

		free_bitmap(ida2, bitmap);
	}

	return 1;
}
EXPORT_SYMBOL(ida2_pre_get);

/**
 * ida2_get_new_above - allocate new ID above or equal to a start id
 * @ida2:	ida2 handle
 * @starting_id: id to start search at
 * @p_id:	pointer to the allocated handle
 *
 * Allocate new ID above or equal to @starting_id.  It should be called
 * with any required locks.
 *
 * If memory is required, it will return %-EAGAIN, you should unlock
 * and go back to the ida2_pre_get() call.  If the ida2 is full, it will
 * return %-ENOSPC.
 *
 * @p_id returns a value in the range @starting_id ... %0x7fffffff.
 */
int ida2_get_new_above(struct ida2 *ida2, int starting_id, int *p_id)
{
	struct idr2_layer *pa[MAX_IDR2_LEVEL + 1];
	struct ida2_bitmap *bitmap;
	unsigned long flags;
	int idr2_id = starting_id / IDA2_BITMAP_BITS;
	int offset = starting_id % IDA2_BITMAP_BITS;
	int t, id;

 restart:
	/* get vacant slot */
	t = idr2_get_empty_slot(&ida2->idr2, idr2_id, pa, 0, &ida2->idr2);
	if (t < 0)
		return t == -ENOMEM ? -EAGAIN : t;

	if (t * IDA2_BITMAP_BITS >= MAX_IDR2_BIT)
		return -ENOSPC;

	if (t != idr2_id)
		offset = 0;
	idr2_id = t;

	/* if bitmap isn't there, create a new one */
	bitmap = (void *)pa[0]->ary[idr2_id & IDR2_MASK];
	if (!bitmap) {
		spin_lock_irqsave(&ida2->idr2.lock, flags);
		bitmap = ida2->free_bitmap;
		ida2->free_bitmap = NULL;
		spin_unlock_irqrestore(&ida2->idr2.lock, flags);

		if (!bitmap)
			return -EAGAIN;

		memset(bitmap, 0, sizeof(struct ida2_bitmap));
		rcu_assign_pointer(pa[0]->ary[idr2_id & IDR2_MASK],
				(void *)bitmap);
		pa[0]->count++;
	}

	/* lookup for empty slot */
	t = find_next_zero_bit(bitmap->bitmap, IDA2_BITMAP_BITS, offset);
	if (t == IDA2_BITMAP_BITS) {
		/* no empty slot after offset, continue to the next chunk */
		idr2_id++;
		offset = 0;
		goto restart;
	}

	id = idr2_id * IDA2_BITMAP_BITS + t;
	if (id >= MAX_IDR2_BIT)
		return -ENOSPC;

	__set_bit(t, bitmap->bitmap);
	if (++bitmap->nr_busy == IDA2_BITMAP_BITS)
		idr2_mark_full(pa, idr2_id);

	*p_id = id;

	/* Each leaf node can handle nearly a thousand slots and the
	 * whole idea of ida2 is to have small memory foot print.
	 * Throw away extra resources one by one after each successful
	 * allocation.
	 */
	if (ida2->idr2.id_free_cnt || ida2->free_bitmap) {
		struct idr2_layer *p = get_from_free_list(&ida2->idr2);
		if (p)
			kmem_cache_free(idr2_layer_cache, p);
	}

	return 0;
}
EXPORT_SYMBOL(ida2_get_new_above);

/**
 * ida2_remove - remove the given ID
 * @ida2:	ida2 handle
 * @id:		ID to free
 */
void ida2_remove(struct ida2 *ida2, int id)
{
	struct idr2_layer *p = ida2->idr2.top;
	int shift = (ida2->idr2.layers - 1) * IDR2_BITS;
	int idr2_id = id / IDA2_BITMAP_BITS;
	int offset = id % IDA2_BITMAP_BITS;
	int n;
	struct ida2_bitmap *bitmap;

	if (idr2_id > idr2_max(ida2->idr2.layers))
		goto err;

	/* clear full bits while looking up the leaf idr2_layer */
	while ((shift > 0) && p) {
		n = (idr2_id >> shift) & IDR2_MASK;
		__clear_bit(n, p->bitmap);
		p = p->ary[n];
		shift -= IDR2_BITS;
	}

	if (p == NULL)
		goto err;

	n = idr2_id & IDR2_MASK;
	__clear_bit(n, p->bitmap);

	bitmap = (void *)p->ary[n];
	if (!bitmap || !test_bit(offset, bitmap->bitmap))
		goto err;

	/* update bitmap and remove it if empty */
	__clear_bit(offset, bitmap->bitmap);
	if (--bitmap->nr_busy == 0) {
		__set_bit(n, p->bitmap);	/* to please idr2_remove() */
		idr2_remove(&ida2->idr2, idr2_id);
		free_bitmap(ida2, bitmap);
	}

	return;

 err:
	WARN(1, "ida2_remove called for id=%d which is not allocated.\n", id);
}
EXPORT_SYMBOL(ida2_remove);

/**
 * ida2_destroy - release all cached layers within an ida2 tree
 * @ida2:		ida2 handle
 */
void ida2_destroy(struct ida2 *ida2)
{
	idr2_destroy(&ida2->idr2);
	kfree(ida2->free_bitmap);
}
EXPORT_SYMBOL(ida2_destroy);

/**
 * ida2_simple_get - get a new id.
 * @ida2: the (initialized) ida2.
 * @start: the minimum id (inclusive, < 0x8000000)
 * @end: the maximum id (exclusive, < 0x8000000 or 0)
 * @gfp_mask: memory allocation flags
 *
 * Allocates an id in the range start <= id < end, or returns -ENOSPC.
 * On memory allocation failure, returns -ENOMEM.
 *
 * Use ida2_simple_remove() to get rid of an id.
 */
int ida2_simple_get(struct ida2 *ida2, unsigned int start, unsigned int end,
		   gfp_t gfp_mask)
{
	int ret, id;
	unsigned int max;
	unsigned long flags;

	BUG_ON((int)start < 0);
	BUG_ON((int)end < 0);

	if (end == 0)
		max = 0x80000000;
	else {
		BUG_ON(end < start);
		max = end - 1;
	}

again:
	if (!ida2_pre_get(ida2, gfp_mask))
		return -ENOMEM;

	spin_lock_irqsave(&simple_ida2_lock, flags);
	ret = ida2_get_new_above(ida2, start, &id);
	if (!ret) {
		if (id > max) {
			ida2_remove(ida2, id);
			ret = -ENOSPC;
		} else {
			ret = id;
		}
	}
	spin_unlock_irqrestore(&simple_ida2_lock, flags);

	if (unlikely(ret == -EAGAIN))
		goto again;

	return ret;
}
EXPORT_SYMBOL(ida2_simple_get);

/**
 * ida2_simple_remove - remove an allocated id.
 * @ida2: the (initialized) ida2.
 * @id: the id returned by ida2_simple_get.
 */
void ida2_simple_remove(struct ida2 *ida2, unsigned int id)
{
	unsigned long flags;

	BUG_ON((int)id < 0);
	spin_lock_irqsave(&simple_ida2_lock, flags);
	ida2_remove(ida2, id);
	spin_unlock_irqrestore(&simple_ida2_lock, flags);
}
EXPORT_SYMBOL(ida2_simple_remove);

/**
 * ida2_init - initialize ida2 handle
 * @ida2:	ida2 handle
 *
 * This function is use to set up the handle (@ida2) that you will pass
 * to the rest of the functions.
 */
void ida2_init(struct ida2 *ida2)
{
	memset(ida2, 0, sizeof(struct ida2));
	idr2_init(&ida2->idr2);

}
EXPORT_SYMBOL(ida2_init);
