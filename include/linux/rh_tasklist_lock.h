// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * RHEL8 ppcle64 arch uses qrwlock for tasklist_lock.
 *
 * Include this header file if tasklist_lock is the only lock accessed by
 * the read_lock/unlock and write_lock_irq/unlock_irq functions. If not,
 * manual replacement of those locking functions by their qread* and qwrite*
 * equivalents is required.
 */
#ifndef __LINUX_RH_TASKLIST_LOCK_H
#define __LINUX_RH_TASKLIST_LOCK_H
#ifdef CONFIG_PPC64

#undef read_lock
#undef read_unlock
#undef write_lock_irq
#undef write_unlock_irq

#define read_lock(l)		qread_lock(l)
#define read_unlock(l)		qread_unlock(l)
#define write_lock_irq(l)	qwrite_lock_irq(l)
#define write_unlock_irq(l)	qwrite_unlock_irq(l)

#define __QRW_LOCK_UNLOCKED(lockname) \
	(qrwlock_t)	{	.raw_lock = __ARCH_RW_LOCK_UNLOCKED,	\
				RW_DEP_MAP_INIT(lockname) }

#define DEFINE_QRWLOCK(x)	qrwlock_t x = __QRW_LOCK_UNLOCKED(x)
#else
#define DEFINE_QRWLOCK(x)	DEFINE_RWLOCK(x)
#endif
#endif
