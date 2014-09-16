#ifndef _LINUX_CPUPRI_H
#define _LINUX_CPUPRI_H

#include <linux/sched.h>

#define CPUPRI_NR_PRIORITIES	(MAX_RT_PRIO + 2)

/* CPUPRI_NR_PRI_WORDS: deprecate since the removal of cpupri_vec->lock */
#define CPUPRI_NR_PRI_WORDS	BITS_TO_LONGS(CPUPRI_NR_PRIORITIES)

#define CPUPRI_INVALID -1
#define CPUPRI_IDLE     0
#define CPUPRI_NORMAL   1
/* values 2-101 are RT priorities 0-99 */

/*
 * spinlock_t lock is now deprecated due to the backport from upstream
 * for BZ1079478. The same upstream change has switched count from int
 * to atomic_t type. Despite the spinlock has been removed upstream, we
 * keep it here to preserve cpupri_vec original size thus avoiding kABI
 * complications. As atomic_t is an opaque int, count preserves the same
 * size and the placed type change shall not imply future kABI issues.
 */
struct cpupri_vec {
	spinlock_t lock;
#ifdef __GENKSYMS__
	int        count;
#else
	atomic_t   count;
#endif
	cpumask_var_t mask;
};

struct cpupri {
	struct cpupri_vec pri_to_cpu[CPUPRI_NR_PRIORITIES];
	/* pri_active: Deprecate since the removal of cpupri_vec->lock */
	long              pri_active[CPUPRI_NR_PRI_WORDS];
	int               cpu_to_pri[NR_CPUS];
};

#ifdef CONFIG_SMP
int  cpupri_find(struct cpupri *cp,
		 struct task_struct *p, struct cpumask *lowest_mask);
void cpupri_set(struct cpupri *cp, int cpu, int pri);
int cpupri_init(struct cpupri *cp, bool bootmem);
void cpupri_cleanup(struct cpupri *cp);
#else
#define cpupri_set(cp, cpu, pri) do { } while (0)
#define cpupri_init() do { } while (0)
#endif

#endif /* _LINUX_CPUPRI_H */
