/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rh_kabi_memcg.h - Red Hat kABI mem_cgroup compatibility structures
 */

#ifndef _LINUX_RH_KABI_MEMCG_H
#define _LINUX_RH_KABI_MEMCG_H

struct mem_cgroup_stat_cpu {
	long count[MEMCG_NR_STAT];
	unsigned long events[NR_VM_EVENT_ITEMS];
	unsigned long nr_page_events;
	unsigned long targets[MEM_CGROUP_NTARGETS];
};

/*
 * per-node information in memory controller.
 */
struct mem_cgroup_per_node {
	struct lruvec		lruvec;

	/* Subtree VM stats (batched updates) */
	struct lruvec_stat __percpu *lruvec_stat_cpu;
	atomic_long_t		lruvec_stat[NR_VM_NODE_STAT_ITEMS];

	unsigned long		lru_zone_size[MAX_NR_ZONES][NR_LRU_LISTS];

	struct mem_cgroup_reclaim_iter iter[DEF_PRIORITY + 1];

	struct rb_node		tree_node;	/* RB tree node */
	unsigned long		usage_in_excess;/* Set to the value by which */
						/* the soft limit is exceeded*/
	bool			on_tree;
	bool			congested;

	struct mem_cgroup	*memcg;		/* Back pointer, we cannot */
						/* use container_of	   */
};

struct mem_cgroup {
	struct cgroup_subsys_state css;

	/* Private memcg ID. Used to ID objects that outlive the cgroup */
	struct mem_cgroup_id id;

	/* Accounted resources */
	struct page_counter memory;
	struct page_counter swap;

	/* Legacy consumer-oriented counters */
	struct page_counter memsw;
	struct page_counter kmem;
	struct page_counter tcpmem;

	/* Upper bound of normal memory consumption range */
	unsigned long high;

	/* Range enforcement for interrupt charges */
	struct work_struct high_work;

	unsigned long soft_limit;

	/* vmpressure notifications */
	struct vmpressure vmpressure;

	/*
	 * Should the accounting and control be hierarchical, per subtree?
	 */
	bool use_hierarchy;

	/* protected by memcg_oom_lock */
	bool		oom_lock;
	int		under_oom;

	int	swappiness;
	/* OOM-Killer disable */
	int		oom_kill_disable;

	/* memory.events */
	struct cgroup_file events_file;

	/* handle for "memory.swap.events" */
	struct cgroup_file swap_events_file;

	/* protect arrays of thresholds */
	struct mutex thresholds_lock;

	/* thresholds for memory usage. RCU-protected */
	struct mem_cgroup_thresholds thresholds;

	/* thresholds for mem+swap usage. RCU-protected */
	struct mem_cgroup_thresholds memsw_thresholds;

	/* For oom notifier event fd */
	struct list_head oom_notify;

	/*
	 * Should we move charges of a task when a task is moved into this
	 * mem_cgroup ? And what type of charges should we move ?
	 */
	unsigned long move_charge_at_immigrate;
	/* taken only while moving_account > 0 */
	spinlock_t		move_lock;
	unsigned long		move_lock_flags;

	MEMCG_PADDING(_pad1_);

	/*
	 * set > 0 if pages under this cgroup are moving to other cgroup.
	 */
	atomic_t		moving_account;
	struct task_struct	*move_lock_task;

	/* memory.stat */
	struct mem_cgroup_stat_cpu __percpu *stat_cpu;

	MEMCG_PADDING(_pad2_);

	atomic_long_t		stat[MEMCG_NR_STAT];
	atomic_long_t		events[NR_VM_EVENT_ITEMS];
	atomic_long_t memory_events[MEMCG_NR_MEMORY_EVENTS];

	unsigned long		socket_pressure;

	/* Legacy tcp memory accounting */
	bool			tcpmem_active;
	int			tcpmem_pressure;

#ifndef CONFIG_SLOB
        /* Index in the kmem_cache->memcg_params.memcg_caches array */
	int kmemcg_id;
	enum memcg_kmem_state kmem_state;
	struct list_head kmem_caches;
#endif

	int last_scanned_node;
#if MAX_NUMNODES > 1
	nodemask_t	scan_nodes;
	atomic_t	numainfo_events;
	atomic_t	numainfo_updating;
#endif

#ifdef CONFIG_CGROUP_WRITEBACK
	struct list_head cgwb_list;
	struct wb_domain cgwb_domain;
#endif

	/* List of events which userspace want to receive */
	struct list_head event_list;
	spinlock_t event_list_lock;

	struct mem_cgroup_per_node *nodeinfo[0];
	/* WARNING: nodeinfo must be the last member here */
};

#endif /* _LINUX_RH_KABI_MEMCG_H */
