#include <linux/cpumask.h>
#include <linux/crash_dump.h>
#include <linux/gfp_types.h>
#include <linux/math.h>
#include <linux/topology.h>

#include "ice_rh.h"

/**
 * ice_rh_get_num_default_rss_queues - default number of RSS queues
 *
 * Default value is the number of physical cores if there are only 1 or 2, or
 * divided by 2 if there are more.
 *
 * This is a renamed copy of netif_get_num_default_rss_queues() from upstream.
 */
int ice_rh_get_num_default_rss_queues(void)
{
	cpumask_var_t cpus;
	int cpu, count = 0;

	if (unlikely(is_kdump_kernel() || !zalloc_cpumask_var(&cpus, GFP_KERNEL)))
		return 1;

	cpumask_copy(cpus, cpu_online_mask);
	for_each_cpu(cpu, cpus) {
		++count;
		cpumask_andnot(cpus, cpus, topology_sibling_cpumask(cpu));
	}
	free_cpumask_var(cpus);

	return count > 2 ? DIV_ROUND_UP(count, 2) : count;
}
