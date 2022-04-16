/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef __ASM_SPINLOCK_H
#define __ASM_SPINLOCK_H
#ifdef __KERNEL__

#ifdef CONFIG_PPC_QUEUED_SPINLOCKS
#include <asm/qspinlock.h>
#include <asm/qrwlock.h>
#else
#include <asm/simple_spinlock.h>
extern void __pv_init_lock_hash(void);
static inline void pv_spinlocks_init(void)
{
	__pv_init_lock_hash();
}
#endif

/*
 * RHEL8 ppcle64 specific qrwlock APIs
 */
typedef struct {
	atomic_long_t raw_lock;	/* 8 bytes */
#ifdef CONFIG_DEBUG_LOCK_ALLOC
	struct lockdep_map dep_map;
#endif
} qrwlock_t;

void qread_lock(qrwlock_t *lock);
void qread_unlock(qrwlock_t *lock);
void qwrite_lock_irq(qrwlock_t *lock);
void qwrite_unlock_irq(qrwlock_t *lock);

#define qrwlock_t		qrwlock_t
#define qread_lock		qread_lock
#define qread_unlock		qread_unlock
#define qwrite_lock_irq		qwrite_lock_irq
#define qwrite_unlock_irq	qwrite_unlock_irq

#endif /* __KERNEL__ */
#endif /* __ASM_SPINLOCK_H */
