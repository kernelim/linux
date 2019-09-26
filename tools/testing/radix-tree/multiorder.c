/*
 * multiorder.c: Multi-order radix tree entry testing
 * Copyright (c) 2016 Intel Corporation
 * Author: Ross Zwisler <ross.zwisler@linux.intel.com>
 * Author: Matthew Wilcox <matthew.r.wilcox@intel.com>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms and conditions of the GNU General Public License,
 * version 2, as published by the Free Software Foundation.
 *
 * This program is distributed in the hope it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 */
#include <linux/radix-tree.h>
#include <linux/slab.h>
#include <linux/errno.h>
#include <pthread.h>

#include "test.h"

void multiorder_iteration(void)
{
	RADIX_TREE(tree, GFP_KERNEL);
	struct radix_tree_iter iter;
	void **slot;
	int i, j, err;

	printv(1, "Multiorder iteration test\n");

#define NUM_ENTRIES 11
	int index[NUM_ENTRIES] = {0, 2, 4, 8, 16, 32, 34, 36, 64, 72, 128};
	int order[NUM_ENTRIES] = {1, 1, 2, 3,  4,  1,  0,  1,  3,  0, 7};

	for (i = 0; i < NUM_ENTRIES; i++) {
		err = item_insert_order(&tree, index[i], order[i]);
		assert(!err);
	}

	for (j = 0; j < 256; j++) {
		for (i = 0; i < NUM_ENTRIES; i++)
			if (j <= (index[i] | ((1 << order[i]) - 1)))
				break;

		radix_tree_for_each_slot(slot, &tree, &iter, j) {
			int height = order[i] / RADIX_TREE_MAP_SHIFT;
			int shift = height * RADIX_TREE_MAP_SHIFT;
			unsigned long mask = (1UL << order[i]) - 1;
			struct item *item = *slot;

			assert((iter.index | mask) == (index[i] | mask));
			assert(iter.shift == shift);
			assert(!radix_tree_is_internal_node(item));
			assert((item->index | mask) == (index[i] | mask));
			assert(item->order == order[i]);
			i++;
		}
	}

	item_kill_tree(&tree);
}

void multiorder_tagged_iteration(void)
{
	RADIX_TREE(tree, GFP_KERNEL);
	struct radix_tree_iter iter;
	void **slot;
	int i, j;

	printv(1, "Multiorder tagged iteration test\n");

#define MT_NUM_ENTRIES 9
	int index[MT_NUM_ENTRIES] = {0, 2, 4, 16, 32, 40, 64, 72, 128};
	int order[MT_NUM_ENTRIES] = {1, 0, 2, 4,  3,  1,  3,  0,   7};

#define TAG_ENTRIES 7
	int tag_index[TAG_ENTRIES] = {0, 4, 16, 40, 64, 72, 128};

	for (i = 0; i < MT_NUM_ENTRIES; i++)
		assert(!item_insert_order(&tree, index[i], order[i]));

	assert(!radix_tree_tagged(&tree, 1));

	for (i = 0; i < TAG_ENTRIES; i++)
		assert(radix_tree_tag_set(&tree, tag_index[i], 1));

	for (j = 0; j < 256; j++) {
		int k;

		for (i = 0; i < TAG_ENTRIES; i++) {
			for (k = i; index[k] < tag_index[i]; k++)
				;
			if (j <= (index[k] | ((1 << order[k]) - 1)))
				break;
		}

		radix_tree_for_each_tagged(slot, &tree, &iter, j, 1) {
			unsigned long mask;
			struct item *item = *slot;
			for (k = i; index[k] < tag_index[i]; k++)
				;
			mask = (1UL << order[k]) - 1;

			assert((iter.index | mask) == (tag_index[i] | mask));
			assert(!radix_tree_is_internal_node(item));
			assert((item->index | mask) == (tag_index[i] | mask));
			assert(item->order == order[k]);
			i++;
		}
	}

	assert(tag_tagged_items(&tree, 0, ~0UL, TAG_ENTRIES, XA_MARK_1,
				XA_MARK_2) == TAG_ENTRIES);

	for (j = 0; j < 256; j++) {
		int mask, k;

		for (i = 0; i < TAG_ENTRIES; i++) {
			for (k = i; index[k] < tag_index[i]; k++)
				;
			if (j <= (index[k] | ((1 << order[k]) - 1)))
				break;
		}

		radix_tree_for_each_tagged(slot, &tree, &iter, j, 2) {
			struct item *item = *slot;
			for (k = i; index[k] < tag_index[i]; k++)
				;
			mask = (1 << order[k]) - 1;

			assert((iter.index | mask) == (tag_index[i] | mask));
			assert(!radix_tree_is_internal_node(item));
			assert((item->index | mask) == (tag_index[i] | mask));
			assert(item->order == order[k]);
			i++;
		}
	}

	assert(tag_tagged_items(&tree, 1, ~0UL, MT_NUM_ENTRIES * 2, XA_MARK_1,
				XA_MARK_0) == TAG_ENTRIES);
	i = 0;
	radix_tree_for_each_tagged(slot, &tree, &iter, 0, 0) {
		assert(iter.index == tag_index[i]);
		i++;
	}

	item_kill_tree(&tree);
}

/*
 * Basic join checks: make sure we can't find an entry in the tree after
 * a larger entry has replaced it
 */
static void multiorder_join1(unsigned long index,
				unsigned order1, unsigned order2)
{
	unsigned long loc;
	void *item, *item2 = item_create(index + 1, order1);
	RADIX_TREE(tree, GFP_KERNEL);

	item_insert_order(&tree, index, order2);
	item = radix_tree_lookup(&tree, index);
	radix_tree_join(&tree, index + 1, order1, item2);
	loc = find_item(&tree, item);
	if (loc == -1)
		free(item);
	item = radix_tree_lookup(&tree, index + 1);
	assert(item == item2);
	item_kill_tree(&tree);
}

/*
 * Check that the accounting of value entries is handled correctly
 * by joining a value entry to a normal pointer.
 */
static void multiorder_join2(unsigned order1, unsigned order2)
{
	RADIX_TREE(tree, GFP_KERNEL);
	struct radix_tree_node *node;
	void *item1 = item_create(0, order1);
	void *item2;

	item_insert_order(&tree, 0, order2);
	radix_tree_insert(&tree, 1 << order2, xa_mk_value(5));
	item2 = __radix_tree_lookup(&tree, 1 << order2, &node, NULL);
	assert(item2 == xa_mk_value(5));
	assert(node->nr_values == 1);

	item2 = radix_tree_lookup(&tree, 0);
	free(item2);

	radix_tree_join(&tree, 0, order1, item1);
	item2 = __radix_tree_lookup(&tree, 1 << order2, &node, NULL);
	assert(item2 == item1);
	assert(node->nr_values == 0);
	item_kill_tree(&tree);
}

/*
 * This test revealed an accounting bug for value entries at one point.
 * Nodes were being freed back into the pool with an elevated exception count
 * by radix_tree_join() and then radix_tree_split() was failing to zero the
 * count of value entries.
 */
static void multiorder_join3(unsigned int order)
{
	RADIX_TREE(tree, GFP_KERNEL);
	struct radix_tree_node *node;
	void **slot;
	struct radix_tree_iter iter;
	unsigned long i;

	for (i = 0; i < (1 << order); i++) {
		radix_tree_insert(&tree, i, xa_mk_value(5));
	}

	radix_tree_join(&tree, 0, order, xa_mk_value(7));
	rcu_barrier();

	radix_tree_split(&tree, 0, 0);

	radix_tree_for_each_slot(slot, &tree, &iter, 0) {
		radix_tree_iter_replace(&tree, &iter, slot, xa_mk_value(5));
	}

	__radix_tree_lookup(&tree, 0, &node, NULL);
	assert(node->nr_values == node->count);

	item_kill_tree(&tree);
}

static void multiorder_join(void)
{
	int i, j, idx;

	for (idx = 0; idx < 1024; idx = idx * 2 + 3) {
		for (i = 1; i < 15; i++) {
			for (j = 0; j < i; j++) {
				multiorder_join1(idx, i, j);
			}
		}
	}

	for (i = 1; i < 15; i++) {
		for (j = 0; j < i; j++) {
			multiorder_join2(i, j);
		}
	}

	for (i = 3; i < 10; i++) {
		multiorder_join3(i);
	}
}

static void check_mem(unsigned old_order, unsigned new_order, unsigned alloc)
{
	struct radix_tree_preload *rtp = &radix_tree_preloads;
	if (rtp->nr != 0)
		printv(2, "split(%u %u) remaining %u\n", old_order, new_order,
							rtp->nr);
	/*
	 * Can't check for equality here as some nodes may have been
	 * RCU-freed while we ran.  But we should never finish with more
	 * nodes allocated since they should have all been preloaded.
	 */
	if (nr_allocated > alloc)
		printv(2, "split(%u %u) allocated %u %u\n", old_order, new_order,
							alloc, nr_allocated);
}

static void __multiorder_split(int old_order, int new_order)
{
	RADIX_TREE(tree, GFP_ATOMIC);
	void **slot;
	struct radix_tree_iter iter;
	unsigned alloc;
	struct item *item;

	radix_tree_preload(GFP_KERNEL);
	assert(item_insert_order(&tree, 0, old_order) == 0);
	radix_tree_preload_end();

	/* Wipe out the preloaded cache or it'll confuse check_mem() */
	radix_tree_cpu_dead(0);

	item = radix_tree_tag_set(&tree, 0, 2);

	radix_tree_split_preload(old_order, new_order, GFP_KERNEL);
	alloc = nr_allocated;
	radix_tree_split(&tree, 0, new_order);
	check_mem(old_order, new_order, alloc);
	radix_tree_for_each_slot(slot, &tree, &iter, 0) {
		radix_tree_iter_replace(&tree, &iter, slot,
					item_create(iter.index, new_order));
	}
	radix_tree_preload_end();

	item_kill_tree(&tree);
	free(item);
}

static void __multiorder_split2(int old_order, int new_order)
{
	RADIX_TREE(tree, GFP_KERNEL);
	void **slot;
	struct radix_tree_iter iter;
	struct radix_tree_node *node;
	void *item;

	__radix_tree_insert(&tree, 0, old_order, xa_mk_value(5));

	item = __radix_tree_lookup(&tree, 0, &node, NULL);
	assert(item == xa_mk_value(5));
	assert(node->nr_values > 0);

	radix_tree_split(&tree, 0, new_order);
	radix_tree_for_each_slot(slot, &tree, &iter, 0) {
		radix_tree_iter_replace(&tree, &iter, slot,
					item_create(iter.index, new_order));
	}

	item = __radix_tree_lookup(&tree, 0, &node, NULL);
	assert(item != xa_mk_value(5));
	assert(node->nr_values == 0);

	item_kill_tree(&tree);
}

static void __multiorder_split3(int old_order, int new_order)
{
	RADIX_TREE(tree, GFP_KERNEL);
	void **slot;
	struct radix_tree_iter iter;
	struct radix_tree_node *node;
	void *item;

	__radix_tree_insert(&tree, 0, old_order, xa_mk_value(5));

	item = __radix_tree_lookup(&tree, 0, &node, NULL);
	assert(item == xa_mk_value(5));
	assert(node->nr_values > 0);

	radix_tree_split(&tree, 0, new_order);
	radix_tree_for_each_slot(slot, &tree, &iter, 0) {
		radix_tree_iter_replace(&tree, &iter, slot, xa_mk_value(7));
	}

	item = __radix_tree_lookup(&tree, 0, &node, NULL);
	assert(item == xa_mk_value(7));
	assert(node->nr_values > 0);

	item_kill_tree(&tree);

	__radix_tree_insert(&tree, 0, old_order, xa_mk_value(5));

	item = __radix_tree_lookup(&tree, 0, &node, NULL);
	assert(item == xa_mk_value(5));
	assert(node->nr_values > 0);

	radix_tree_split(&tree, 0, new_order);
	radix_tree_for_each_slot(slot, &tree, &iter, 0) {
		if (iter.index == (1 << new_order))
			radix_tree_iter_replace(&tree, &iter, slot,
						xa_mk_value(7));
		else
			radix_tree_iter_replace(&tree, &iter, slot, NULL);
	}

	item = __radix_tree_lookup(&tree, 1 << new_order, &node, NULL);
	assert(item == xa_mk_value(7));
	assert(node->count == node->nr_values);
	do {
		node = node->parent;
		if (!node)
			break;
		assert(node->count == 1);
		assert(node->nr_values == 0);
	} while (1);

	item_kill_tree(&tree);
}

static void multiorder_split(void)
{
	int i, j;

	for (i = 3; i < 11; i++)
		for (j = 0; j < i; j++) {
			__multiorder_split(i, j);
			__multiorder_split2(i, j);
			__multiorder_split3(i, j);
		}
}

bool stop_iteration = false;

static void *creator_func(void *ptr)
{
	/* 'order' is set up to ensure we have sibling entries */
	unsigned int order = RADIX_TREE_MAP_SHIFT - 1;
	struct radix_tree_root *tree = ptr;
	int i;

	for (i = 0; i < 10000; i++) {
		item_insert_order(tree, 0, order);
		item_delete_rcu(tree, 0);
	}

	stop_iteration = true;
	return NULL;
}

static void *iterator_func(void *ptr)
{
	struct radix_tree_root *tree = ptr;
	struct radix_tree_iter iter;
	struct item *item;
	void **slot;

	while (!stop_iteration) {
		rcu_read_lock();
		radix_tree_for_each_slot(slot, tree, &iter, 0) {
			item = radix_tree_deref_slot(slot);

			if (!item)
				continue;
			if (radix_tree_deref_retry(item)) {
				slot = radix_tree_iter_retry(&iter);
				continue;
			}

			item_sanity(item, iter.index);
		}
		rcu_read_unlock();
	}
	return NULL;
}

static void multiorder_iteration_race(void)
{
	const int num_threads = sysconf(_SC_NPROCESSORS_ONLN);
	pthread_t worker_thread[num_threads];
	RADIX_TREE(tree, GFP_KERNEL);
	int i;

	pthread_create(&worker_thread[0], NULL, &creator_func, &tree);
	for (i = 1; i < num_threads; i++)
		pthread_create(&worker_thread[i], NULL, &iterator_func, &tree);

	for (i = 0; i < num_threads; i++)
		pthread_join(worker_thread[i], NULL);

	item_kill_tree(&tree);
}

void multiorder_checks(void)
{
	multiorder_iteration();
	multiorder_tagged_iteration();
	multiorder_join();
	multiorder_split();
	multiorder_iteration_race();

	radix_tree_cpu_dead(0);
}

int __weak main(void)
{
	radix_tree_init();
	multiorder_checks();
	return 0;
}
