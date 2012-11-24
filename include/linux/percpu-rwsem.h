#ifndef _LINUX_PERCPU_RWSEM_H
#define _LINUX_PERCPU_RWSEM_H

#include <linux/mutex.h>
#include <linux/percpu.h>
#include <linux/rcupdate.h>
#include <linux/delay.h>
#include <asm/local.h>

struct percpu_rw_semaphore {
	local_t __percpu *counters;
	bool locked;
	struct mutex mtx;
};

static inline void percpu_down_read(struct percpu_rw_semaphore *p)
{
	rcu_read_lock();
	if (unlikely(p->locked)) {
		rcu_read_unlock();
		mutex_lock(&p->mtx);
		preempt_disable();
		local_inc(this_cpu_ptr(p->counters));
		preempt_enable();
		mutex_unlock(&p->mtx);
		return;
	}
	preempt_disable();
	local_inc(this_cpu_ptr(p->counters));
	preempt_enable();
	rcu_read_unlock();
}

static inline void percpu_up_read(struct percpu_rw_semaphore *p)
{
	/*
	 * On X86, write operation in local_dec serves as a memory unlock
	 * barrier (i.e. memory accesses may be moved before the write, but
	 * no memory accesses are moved past the write).
	 * On other architectures this may not be the case, so we need smp_mb()
	 * there.
	 */
#if defined(CONFIG_X86) && (!defined(CONFIG_X86_PPRO_FENCE) && !defined(CONFIG_X86_OOSTORE))
	barrier();
#else
	smp_mb();
#endif
	preempt_disable();
	local_dec(this_cpu_ptr(p->counters));
	preempt_enable();
}

static inline unsigned long __percpu_count(local_t __percpu *counters)
{
	unsigned long total = 0;
	int cpu;

	for_each_possible_cpu(cpu)
		total += local_read(per_cpu_ptr(counters, cpu));

	return total;
}

static inline void percpu_down_write(struct percpu_rw_semaphore *p)
{
	mutex_lock(&p->mtx);
	p->locked = true;
	synchronize_rcu();
	while (__percpu_count(p->counters))
		msleep(1);
	smp_rmb(); /* paired with smp_mb() in percpu_sem_up_read() */
}

static inline void percpu_up_write(struct percpu_rw_semaphore *p)
{
	p->locked = false;
	mutex_unlock(&p->mtx);
}

static inline int percpu_init_rwsem(struct percpu_rw_semaphore *p)
{
	int cpu;
	p->counters = alloc_percpu(local_t);
	if (unlikely(!p->counters))
		return -ENOMEM;
	for_each_possible_cpu(cpu)
		local_set(per_cpu_ptr(p->counters, cpu), 0);
	p->locked = false;
	mutex_init(&p->mtx);
	return 0;
}

static inline void percpu_free_rwsem(struct percpu_rw_semaphore *p)
{
	free_percpu(p->counters);
	p->counters = NULL; /* catch use after free bugs */
}

#endif
