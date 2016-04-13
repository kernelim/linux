/*
 *  include/asm-s390/spinlock.h
 *
 *  S390 version
 *    Copyright (C) 1999 IBM Deutschland Entwicklung GmbH, IBM Corporation
 *    Author(s): Martin Schwidefsky (schwidefsky@de.ibm.com)
 *
 *  Derived from "include/asm-i386/spinlock.h"
 */

#ifndef __ASM_SPINLOCK_H
#define __ASM_SPINLOCK_H

#include <linux/smp.h>

#define SPINLOCK_LOCKVAL (S390_lowcore.spinlock_lockval)

#if __GNUC__ > 3 || (__GNUC__ == 3 && __GNUC_MINOR__ > 2)

static inline int
_raw_compare_and_swap(unsigned int *lock, unsigned int old, unsigned int new)
{
	unsigned int old_expected = old;

	asm volatile(
		"	cs	%0,%3,%1"
		: "=d" (old), "=Q" (*lock)
		: "0" (old), "d" (new), "Q" (*lock)
		: "cc", "memory" );
	return old == old_expected;
}

#else /* __GNUC__ */

static inline int
_raw_compare_and_swap(unsigned int *lock, unsigned int old, unsigned int new)
{
	unsigned int old_expected = old;

	asm volatile(
		"	cs	%0,%3,0(%4)"
		: "=d" (old), "=m" (*lock)
		: "0" (old), "d" (new), "a" (lock), "m" (*lock)
		: "cc", "memory" );
	return old == old_expected;
}

#endif /* __GNUC__ */

/*
 * Simple spin lock operations.  There are two variants, one clears IRQ's
 * on the local processor, one does not.
 *
 * We make no fairness assumptions. They have a cost.
 *
 * (the type definitions are in asm/spinlock_types.h)
 */

void _raw_spin_lock_wait(raw_spinlock_t *);
int _raw_spin_trylock_retry(raw_spinlock_t *);
void _raw_spin_relax(raw_spinlock_t *);
void _raw_spin_lock_wait_flags(raw_spinlock_t *, unsigned long flags);

static inline u32 __raw_spin_lockval(int cpu)
{
	return ~cpu;
}

static inline int __raw_spin_value_unlocked(raw_spinlock_t lock)
{
	return lock.lock == 0;
}

static inline int __raw_spin_is_locked(raw_spinlock_t *lp)
{
	return ACCESS_ONCE(lp->lock) != 0;
}

static inline int __raw_spin_trylock_once(raw_spinlock_t *lp)
{
	barrier();
	return likely(__raw_spin_value_unlocked(*lp) &&
		      _raw_compare_and_swap(&lp->lock, 0, SPINLOCK_LOCKVAL));
}

static inline void __raw_spin_lock(raw_spinlock_t *lp)
{
	if (!__raw_spin_trylock_once(lp))
		_raw_spin_lock_wait(lp);
}

static inline void __raw_spin_lock_flags(raw_spinlock_t *lp,
					 unsigned long flags)
{
	if (!__raw_spin_trylock_once(lp))
		_raw_spin_lock_wait_flags(lp, flags);
}

static inline int __raw_spin_trylock(raw_spinlock_t *lp)
{
	if (!__raw_spin_trylock_once(lp))
		return _raw_spin_trylock_retry(lp);
	return 1;
}

static inline void __raw_spin_unlock(raw_spinlock_t *lp)
{
	typecheck(unsigned int, lp->lock);
	asm volatile(
		"bcr	15,0\n"
		"st	%1,%0\n"
		: "+Q" (lp->lock)
		: "d" (0)
		: "cc", "memory");
}

static inline void __raw_spin_unlock_wait(raw_spinlock_t *lock)
{
	while (__raw_spin_is_locked(lock))
		_raw_spin_relax(lock);
}

/*
 * Read-write spinlocks, allowing multiple readers
 * but only one writer.
 *
 * NOTE! it is quite common to have readers in interrupts
 * but no interrupt writers. For those circumstances we
 * can "mix" irq-safe locks - any writer needs to get a
 * irq-safe write-lock, but readers can get non-irqsafe
 * read-locks.
 */

/**
 * read_can_lock - would read_trylock() succeed?
 * @lock: the rwlock in question.
 */
#define __raw_read_can_lock(x) ((int)(x)->lock >= 0)

/**
 * write_can_lock - would write_trylock() succeed?
 * @lock: the rwlock in question.
 */
#define __raw_write_can_lock(x) ((x)->lock == 0)

extern void _raw_read_lock_wait(raw_rwlock_t *lp);
extern void _raw_read_lock_wait_flags(raw_rwlock_t *lp, unsigned long flags);
extern int _raw_read_trylock_retry(raw_rwlock_t *lp);
extern void _raw_write_lock_wait(raw_rwlock_t *lp);
extern void _raw_write_lock_wait_flags(raw_rwlock_t *lp, unsigned long flags);
extern int _raw_write_trylock_retry(raw_rwlock_t *lp);

static inline int __raw_read_trylock_once(raw_rwlock_t *rw)
{
	unsigned int old = ACCESS_ONCE(rw->lock);
	return likely((int) old >= 0 &&
		      _raw_compare_and_swap(&rw->lock, old, old + 1));
}

static inline int __raw_write_trylock_once(raw_rwlock_t *rw)
{
	unsigned int old = ACCESS_ONCE(rw->lock);
	return likely(old == 0 &&
		      _raw_compare_and_swap(&rw->lock, 0, 0x80000000));
}

static inline void __raw_read_lock(raw_rwlock_t *rw)
{
	if (!__raw_read_trylock_once(rw))
		_raw_read_lock_wait(rw);
}

static inline void __raw_read_lock_flags(raw_rwlock_t *rw, unsigned long flags)
{
	if (!__raw_read_trylock_once(rw))
		_raw_read_lock_wait_flags(rw, flags);
}

static inline void __raw_read_unlock(raw_rwlock_t *rw)
{
	unsigned int old;

	do {
		old = ACCESS_ONCE(rw->lock);
	} while (!_raw_compare_and_swap(&rw->lock, old, old - 1));
}

static inline void __raw_write_lock(raw_rwlock_t *rw)
{
	if (!__raw_write_trylock_once(rw))
		_raw_write_lock_wait(rw);
}

static inline void __raw_write_lock_flags(raw_rwlock_t *rw, unsigned long flags)
{
	if (!__raw_write_trylock_once(rw))
		_raw_write_lock_wait_flags(rw, flags);
}

static inline void __raw_write_unlock(raw_rwlock_t *rw)
{
	typecheck(unsigned int, rw->lock);
	asm volatile(
		"bcr	15,0\n"
		"st	%1,%0\n"
		: "+Q" (rw->lock)
		: "d" (0)
		: "cc", "memory");
}

static inline int __raw_read_trylock(raw_rwlock_t *rw)
{
	if (!__raw_read_trylock_once(rw))
		return _raw_read_trylock_retry(rw);
	return 1;
}

static inline int __raw_write_trylock(raw_rwlock_t *rw)
{
	if (!__raw_write_trylock_once(rw))
		return _raw_write_trylock_retry(rw);
	return 1;
}

#define _raw_read_relax(lock)	cpu_relax()
#define _raw_write_relax(lock)	cpu_relax()

#define __always_inline__spin_lock
#define __always_inline__read_lock
#define __always_inline__write_lock
#define __always_inline__spin_lock_bh
#define __always_inline__read_lock_bh
#define __always_inline__write_lock_bh
#define __always_inline__spin_lock_irq
#define __always_inline__read_lock_irq
#define __always_inline__write_lock_irq
#define __always_inline__spin_lock_irqsave
#define __always_inline__read_lock_irqsave
#define __always_inline__write_lock_irqsave
#define __always_inline__spin_trylock
#define __always_inline__read_trylock
#define __always_inline__write_trylock
#define __always_inline__spin_trylock_bh
#define __always_inline__spin_unlock
#define __always_inline__read_unlock
#define __always_inline__write_unlock
#define __always_inline__spin_unlock_bh
#define __always_inline__read_unlock_bh
#define __always_inline__write_unlock_bh
#define __always_inline__spin_unlock_irq
#define __always_inline__read_unlock_irq
#define __always_inline__write_unlock_irq
#define __always_inline__spin_unlock_irqrestore
#define __always_inline__read_unlock_irqrestore
#define __always_inline__write_unlock_irqrestore

#endif /* __ASM_SPINLOCK_H */
