/*
 * Copyright (C) 2013 Red Hat
 *
 * This file is subject to the terms and conditions of the GNU General Public
 * License v2. See the file COPYING in the main directory of this archive for
 * more details.
 */

#ifndef DRM_BACKPORT_H_
#define DRM_BACKPORT_H_

#include <linux/console.h>

#include <linux/pci.h>
#include <linux/pci_hotplug.h>

#define in_dbg_master() (0)

static inline void console_lock(void)
{
	acquire_console_sem();
}

static inline void console_unlock(void)
{
	release_console_sem();
}

static inline int console_trylock(void)
{
	return try_acquire_console_sem();
}

static inline struct inode *file_inode(struct file *f)
{
	return f->f_path.dentry->d_inode;
}

#define SIZE_MAX ULONG_MAX

/**
 * mod_delayed_work - modify delay of or queue a delayed work
 * @wq: workqueue to use
 * @dwork: work to queue
 * @delay: number of jiffies to wait before queueing
 *
 * mod_delayed_work_on() on local CPU.
 *
 * WARNING: unlike upstream mod_delayed_work() from newer kernel,
 * this is not safe for atomic ctx!  Be sure to review call sites.
 */
static inline bool mod_delayed_work(struct workqueue_struct *wq,
				    struct delayed_work *dwork,
				    unsigned long delay)
{
	int ret = cancel_delayed_work(dwork);
	queue_delayed_work(wq, dwork, delay);
	return ret;
}

#define __wait_event_lock_irq(wq, condition, lock, cmd)			\
do {									\
	DEFINE_WAIT(__wait);						\
									\
	for (;;) {							\
		prepare_to_wait(&wq, &__wait, TASK_UNINTERRUPTIBLE);	\
		if (condition)						\
			break;						\
		spin_unlock_irq(&lock);					\
		cmd;							\
		schedule();						\
		spin_lock_irq(&lock);					\
	}								\
	finish_wait(&wq, &__wait);					\
} while (0)

/**
 * wait_event_lock_irq_cmd - sleep until a condition gets true. The
 *			     condition is checked under the lock. This
 *			     is expected to be called with the lock
 *			     taken.
 * @wq: the waitqueue to wait on
 * @condition: a C expression for the event to wait for
 * @lock: a locked spinlock_t, which will be released before cmd
 *	  and schedule() and reacquired afterwards.
 * @cmd: a command which is invoked outside the critical section before
 *	 sleep
 *
 * The process is put to sleep (TASK_UNINTERRUPTIBLE) until the
 * @condition evaluates to true. The @condition is checked each time
 * the waitqueue @wq is woken up.
 *
 * wake_up() has to be called after changing any variable that could
 * change the result of the wait condition.
 *
 * This is supposed to be called while holding the lock. The lock is
 * dropped before invoking the cmd and going to sleep and is reacquired
 * afterwards.
 */
#define wait_event_lock_irq_cmd(wq, condition, lock, cmd)		\
do {									\
	if (condition)							\
		break;							\
	__wait_event_lock_irq(wq, condition, lock, cmd);		\
} while (0)

/**
 * wait_event_lock_irq - sleep until a condition gets true. The
 *			 condition is checked under the lock. This
 *			 is expected to be called with the lock
 *			 taken.
 * @wq: the waitqueue to wait on
 * @condition: a C expression for the event to wait for
 * @lock: a locked spinlock_t, which will be released before schedule()
 *	  and reacquired afterwards.
 *
 * The process is put to sleep (TASK_UNINTERRUPTIBLE) until the
 * @condition evaluates to true. The @condition is checked each time
 * the waitqueue @wq is woken up.
 *
 * wake_up() has to be called after changing any variable that could
 * change the result of the wait condition.
 *
 * This is supposed to be called while holding the lock. The lock is
 * dropped before going to sleep and is reacquired afterwards.
 */
#define wait_event_lock_irq(wq, condition, lock)			\
do {									\
	if (condition)							\
		break;							\
	__wait_event_lock_irq(wq, condition, lock, );			\
} while (0)


#define __wait_event_interruptible_lock_irq(wq, condition,		\
					    lock, ret, cmd)		\
do {									\
	DEFINE_WAIT(__wait);						\
									\
	for (;;) {							\
		prepare_to_wait(&wq, &__wait, TASK_INTERRUPTIBLE);	\
		if (condition)						\
			break;						\
		if (signal_pending(current)) {				\
			ret = -ERESTARTSYS;				\
			break;						\
		}							\
		spin_unlock_irq(&lock);					\
		cmd;							\
		schedule();						\
		spin_lock_irq(&lock);					\
	}								\
	finish_wait(&wq, &__wait);					\
} while (0)

/**
 * wait_event_interruptible_lock_irq_cmd - sleep until a condition gets true.
 *		The condition is checked under the lock. This is expected to
 *		be called with the lock taken.
 * @wq: the waitqueue to wait on
 * @condition: a C expression for the event to wait for
 * @lock: a locked spinlock_t, which will be released before cmd and
 *	  schedule() and reacquired afterwards.
 * @cmd: a command which is invoked outside the critical section before
 *	 sleep
 *
 * The process is put to sleep (TASK_INTERRUPTIBLE) until the
 * @condition evaluates to true or a signal is received. The @condition is
 * checked each time the waitqueue @wq is woken up.
 *
 * wake_up() has to be called after changing any variable that could
 * change the result of the wait condition.
 *
 * This is supposed to be called while holding the lock. The lock is
 * dropped before invoking the cmd and going to sleep and is reacquired
 * afterwards.
 *
 * The macro will return -ERESTARTSYS if it was interrupted by a signal
 * and 0 if @condition evaluated to true.
 */
#define wait_event_interruptible_lock_irq_cmd(wq, condition, lock, cmd)	\
({									\
	int __ret = 0;							\
									\
	if (!(condition))						\
		__wait_event_interruptible_lock_irq(wq, condition,	\
						    lock, __ret, cmd);	\
	__ret;								\
})

/**
 * wait_event_interruptible_lock_irq - sleep until a condition gets true.
 *		The condition is checked under the lock. This is expected
 *		to be called with the lock taken.
 * @wq: the waitqueue to wait on
 * @condition: a C expression for the event to wait for
 * @lock: a locked spinlock_t, which will be released before schedule()
 *	  and reacquired afterwards.
 *
 * The process is put to sleep (TASK_INTERRUPTIBLE) until the
 * @condition evaluates to true or signal is received. The @condition is
 * checked each time the waitqueue @wq is woken up.
 *
 * wake_up() has to be called after changing any variable that could
 * change the result of the wait condition.
 *
 * This is supposed to be called while holding the lock. The lock is
 * dropped before going to sleep and is reacquired afterwards.
 *
 * The macro will return -ERESTARTSYS if it was interrupted by a signal
 * and 0 if @condition evaluated to true.
 */
#define wait_event_interruptible_lock_irq(wq, condition, lock)		\
({									\
	int __ret = 0;							\
									\
	if (!(condition))						\
		__wait_event_interruptible_lock_irq(wq, condition,	\
						    lock, __ret, );	\
	__ret;								\
})


#endif /* DRM_BACKPORT_H_ */

