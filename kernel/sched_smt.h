#ifdef CONFIG_SCHED_SMT
/*
 * This code is specific to x86-64.
 */
atomic_t sched_smt_present __read_mostly;

void sched_cpu_activate(unsigned int cpu)
{
#ifdef CONFIG_X86_64
	/*
	 * When going up, increment the number of cores with SMT present.
	 */
	if (cpumask_weight(cpu_sibling_mask(cpu)) == 2)
		atomic_inc(&sched_smt_present);
#endif
}

void sched_cpu_deactivate(unsigned int cpu)
{
#ifdef CONFIG_X86_64
	/*
	 * When going down, decrement the number of cores with SMT present.
	 */
	if (cpumask_weight(cpu_sibling_mask(cpu)) == 2)
		atomic_dec(&sched_smt_present);
#endif
}
#endif /* CONFIG_SCHED_SMT */
