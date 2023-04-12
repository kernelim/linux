/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_SCHED_SYSCTL_H
#define _LINUX_SCHED_SYSCTL_H

#include <linux/types.h>

struct ctl_table;

#ifdef CONFIG_DETECT_HUNG_TASK

#ifdef CONFIG_SMP
extern unsigned int sysctl_hung_task_all_cpu_backtrace;
#else
#define sysctl_hung_task_all_cpu_backtrace 0
#endif /* CONFIG_SMP */

extern int	     sysctl_hung_task_check_count;
extern unsigned int  sysctl_hung_task_panic;
extern unsigned long sysctl_hung_task_timeout_secs;
extern unsigned long sysctl_hung_task_check_interval_secs;
extern int sysctl_hung_task_warnings;
int proc_dohung_task_timeout_secs(struct ctl_table *table, int write,
		void *buffer, size_t *lenp, loff_t *ppos);
#else
/* Avoid need for ifdefs elsewhere in the code */
enum { sysctl_hung_task_timeout_secs = 0 };
#endif

enum sched_tunable_scaling {
	SCHED_TUNABLESCALING_NONE,
	SCHED_TUNABLESCALING_LOG,
	SCHED_TUNABLESCALING_LINEAR,
	SCHED_TUNABLESCALING_END,
};

#define NUMA_BALANCING_DISABLED		0x0
#define NUMA_BALANCING_NORMAL		0x1
#define NUMA_BALANCING_MEMORY_TIERING	0x2

#ifdef CONFIG_NUMA_BALANCING
extern int sysctl_numa_balancing_mode;
#else
#define sysctl_numa_balancing_mode	0
#endif

int sysctl_numa_balancing(struct ctl_table *table, int write, void *buffer,
		size_t *lenp, loff_t *ppos);

#endif /* _LINUX_SCHED_SYSCTL_H */
