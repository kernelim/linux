// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * This file is specific to RHEL8 ppcle64 architecture. Its purpose is to
 * enable the use of qrwlock for tasklist_lock. Qspinlock will be used
 * for fair queuing in qrwlock.
 */
#define CONFIG_PPC_QUEUED_SPINLOCKS
#define CONFIG_QUEUED_SPINLOCKS
#define CONFIG_QUEUED_RWLOCKS
#define CONFIG_PARAVIRT_SPINLOCKS

#ifdef CONFIG_DEBUG_SPINLOCK
#undef CONFIG_DEBUG_SPINLOCK
#endif

#include <linux/spinlock.h>
#include "../../../kernel/locking/qspinlock.c"
#include "../../../kernel/locking/qrwlock.c"

void qread_lock(qrwlock_t *lock)
{
	__raw_read_lock((rwlock_t *)lock);
}

void qread_unlock(qrwlock_t *lock)
{
	__raw_read_unlock((rwlock_t *)lock);
}

void qwrite_lock_irq(qrwlock_t *lock)
{
	__raw_write_lock_irq((rwlock_t *)lock);
}

void qwrite_unlock_irq(qrwlock_t *lock)
{
	__raw_write_unlock_irq((rwlock_t *)lock);
}
