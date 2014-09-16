/*
 * kernel/mutex.c
 *
 * Mutexes: blocking mutual exclusion locks
 *
 * Started by Ingo Molnar:
 *
 *  Copyright (C) 2004, 2005, 2006 Red Hat, Inc., Ingo Molnar <mingo@redhat.com>
 *
 * Many thanks to Arjan van de Ven, Thomas Gleixner, Steven Rostedt and
 * David Howells for suggestions and improvements.
 *
 *  - Adaptive spinning for mutexes by Peter Zijlstra. (Ported to mainline
 *    from the -rt tree, where it was originally implemented for rtmutexes
 *    by Steven Rostedt, based on work by Gregory Haskins, Peter Morreale
 *    and Sven Dietrich.
 *
 * Also see Documentation/mutex-design.txt.
 */
#include <linux/mutex.h>
#include <linux/ww_mutex.h>
#include <linux/sched.h>
#include <linux/module.h>
#include <linux/spinlock.h>
#include <linux/interrupt.h>
#include <linux/debug_locks.h>
#include <linux/percpu.h>

/*
 * In the DEBUG case we are using the "NULL fastpath" for mutexes,
 * which forces all calls into the slowpath:
 */
#ifdef CONFIG_DEBUG_MUTEXES
# include "mutex-debug.h"
# include <asm-generic/mutex-null.h>
/*
 * Must be 0 for the debug case so we do not do the unlock outside of the
 * wait_lock region. debug_mutex_unlock() will do the actual unlock in this
 * case.
 */
# undef __mutex_slowpath_needs_to_unlock
# define  __mutex_slowpath_needs_to_unlock()   0
#else
# include "mutex.h"
# include <asm/mutex.h>
#endif

/*
 * A negative mutex count indicates that waiters are sleeping waiting for the
 * mutex.
 */
#define	MUTEX_SHOW_NO_WAITER(mutex)	(atomic_read(&(mutex)->count) >= 0)

/***
 * mutex_init - initialize the mutex
 * @lock: the mutex to be initialized
 * @key: the lock_class_key for the class; used by mutex lock debugging
 *
 * Initialize the mutex to unlocked state.
 *
 * It is not allowed to initialize an already locked mutex.
 */
void
__mutex_init(struct mutex *lock, const char *name, struct lock_class_key *key)
{
	atomic_set(&lock->count, 1);
	spin_lock_init(&lock->wait_lock);
	MUTEX_INIT_WAIT_LIST(&lock->wait_list);
	mutex_clear_owner(lock);
#if defined(CONFIG_SMP) && !defined(CONFIG_DEBUG_MUTEXES) && \
    !defined(CONFIG_HAVE_DEFAULT_NO_SPIN_MUTEXES)
	lock->spin_mlock = NULL;
#endif

	debug_mutex_init(lock, name, key);
}

EXPORT_SYMBOL(__mutex_init);

#ifndef CONFIG_DEBUG_LOCK_ALLOC
/*
 * We split the mutex lock/unlock logic into separate fastpath and
 * slowpath functions, to reduce the register pressure on the fastpath.
 * We also put the fastpath first in the kernel image, to make sure the
 * branch is predicted by the CPU as default-untaken.
 */
static __used noinline void __sched
__mutex_lock_slowpath(atomic_t *lock_count);

/***
 * mutex_lock - acquire the mutex
 * @lock: the mutex to be acquired
 *
 * Lock the mutex exclusively for this task. If the mutex is not
 * available right now, it will sleep until it can get it.
 *
 * The mutex must later on be released by the same task that
 * acquired it. Recursive locking is not allowed. The task
 * may not exit without first unlocking the mutex. Also, kernel
 * memory where the mutex resides mutex must not be freed with
 * the mutex still locked. The mutex must first be initialized
 * (or statically defined) before it can be locked. memset()-ing
 * the mutex to 0 is not allowed.
 *
 * ( The CONFIG_DEBUG_MUTEXES .config option turns on debugging
 *   checks that will enforce the restrictions and will also do
 *   deadlock debugging. )
 *
 * This function is similar to (but not equivalent to) down().
 */
void __sched mutex_lock(struct mutex *lock)
{
	might_sleep();
	/*
	 * The locking fastpath is the 1->0 transition from
	 * 'unlocked' into 'locked' state.
	 */
	__mutex_fastpath_lock(&lock->count, __mutex_lock_slowpath);
	mutex_set_owner(lock);
}

EXPORT_SYMBOL(mutex_lock);
#endif

#if defined(CONFIG_SMP) && !defined(CONFIG_DEBUG_MUTEXES) && \
    !defined(CONFIG_HAVE_DEFAULT_NO_SPIN_MUTEXES)
/*
 * In order to avoid a stampede of mutex spinners from acquiring the mutex
 * more or less simultaneously, the spinners need to acquire a MCS lock
 * first before spinning on the owner field.
 */
struct mspin_node {
	struct mspin_node *next ;
	int		  locked;	/* 1 if lock acquired */
};

/*
 * Cancellable version of the MCS lock above.
 *
 * Intended for adaptive spinning of sleeping locks:
 * mutex_lock()/rwsem_down_{read,write}() etc.
 */
struct optimistic_spin_queue {
	struct optimistic_spin_queue *next, *prev;
	int locked; /* 1 if lock acquired */
};
#define OSQ_LOCK(mutex)	((struct optimistic_spin_queue **)&((mutex)->spin_mlock))

/*
 * An MCS like lock especially tailored for optimistic spinning for sleeping
 * lock implementations (mutex, rwsem, etc).
 *
 * Using a single mcs node per CPU is safe because sleeping locks should not be
 * called from interrupt context and we have preemption disabled while
 * spinning.
 */
static DEFINE_PER_CPU_SHARED_ALIGNED(struct optimistic_spin_queue, osq_node);

/*
 * Get a stable @node->next pointer, either for unlock() or unqueue() purposes.
 * Can return NULL in case we were the last queued and we updated @lock instead.
 */
static inline struct optimistic_spin_queue *
osq_wait_next(struct optimistic_spin_queue **lock,
	      struct optimistic_spin_queue *node,
	      struct optimistic_spin_queue *prev)
{
	struct optimistic_spin_queue *next = NULL;

	for (;;) {
		if (*lock == node && cmpxchg(lock, node, prev) == node) {
			/*
			 * We were the last queued, we moved @lock back. @prev
			 * will now observe @lock and will complete its
			 * unlock()/unqueue().
			 */
			break;
		}

		/*
		 * We must xchg() the @node->next value, because if we were to
		 * leave it in, a concurrent unlock()/unqueue() from
		 * @node->next might complete Step-A and think its @prev is
		 * still valid.
		 *
		 * If the concurrent unlock()/unqueue() wins the race, we'll
		 * wait for either @lock to point to us, through its Step-B, or
		 * wait for a new @node->next from its Step-C.
		 */
		if (node->next) {
			next = xchg(&node->next, NULL);
			if (next)
				break;
		}

		arch_mutex_cpu_relax();
	}

	return next;
}

bool osq_lock(struct mutex *mutex, struct optimistic_spin_queue **lock)
{
	struct optimistic_spin_queue *node
					= this_cpu_ptr(&per_cpu_var(osq_node));
	struct optimistic_spin_queue *prev, *next;

	node->locked = 0;
	node->next = NULL;

	prev = xchg(lock, node);
	/*
	 * In case the mutex is initialized with the DEFINE_MUTEX() macro,
	 * the check below will correctly handle that initial value.
	 */
	if (unlikely(prev == (struct optimistic_spin_queue *)&mutex->wait_list))
		prev = NULL;
	node->prev = prev;
	if (likely(prev == NULL))
		return true;

	ACCESS_ONCE(prev->next) = node;

	/*
	 * Normally @prev is untouchable after the above store; because at that
	 * moment unlock can proceed and wipe the node element from stack.
	 *
	 * However, since our nodes are static per-cpu storage, we're
	 * guaranteed their existence -- this allows us to apply
	 * cmpxchg in an attempt to undo our queueing.
	 */

	while (!node->locked) {
		/*
		 * If we need to reschedule bail... so we can block.
		 */
		if (need_resched())
			goto unqueue;

		arch_mutex_cpu_relax();
	}
	return true;

unqueue:
	/*
	 * Step - A  -- stabilize @prev
	 *
	 * Undo our @prev->next assignment; this will make @prev's
	 * unlock()/unqueue() wait for a next pointer since @lock points to us
	 * (or later).
	 */

	for (;;) {
		if (prev->next == node &&
		    cmpxchg(&prev->next, node, NULL) == node)
			break;

		/*
		 * We can only fail the cmpxchg() racing against an unlock(),
		 * in which case we should observe @node->locked becomming
		 * true.
		 */
		if (node->locked)
			return true;

		arch_mutex_cpu_relax();

		/*
		 * Or we race against a concurrent unqueue()'s step-B, in which
		 * case its step-C will write us a new @node->prev pointer.
		 */
		prev = ACCESS_ONCE(node->prev);
	}

	/*
	 * Step - B -- stabilize @next
	 *
	 * Similar to unlock(), wait for @node->next or move @lock from @node
	 * back to @prev.
	 */

	next = osq_wait_next(lock, node, prev);
	if (!next)
		return false;

	/*
	 * Step - C -- unlink
	 *
	 * @prev is stable because its still waiting for a new @prev->next
	 * pointer, @next is stable because our @node->next pointer is NULL and
	 * it will wait in Step-A.
	 */

	ACCESS_ONCE(next->prev) = prev;
	ACCESS_ONCE(prev->next) = next;

	return false;
}

void osq_unlock(struct optimistic_spin_queue **lock)
{
	struct optimistic_spin_queue *node
					= this_cpu_ptr(&per_cpu_var(osq_node));
	struct optimistic_spin_queue *next;

	/*
	 * Fast path for the uncontended case.
	 */
	if (likely(cmpxchg(lock, node, NULL) == node))
		return;

	/*
	 * Second most likely case.
	 */
	next = xchg(&node->next, NULL);
	if (next) {
		ACCESS_ONCE(next->locked) = 1;
		return;
	}

	next = osq_wait_next(lock, node, NULL);
	if (next)
		ACCESS_ONCE(next->locked) = 1;
}

#endif /* CONFIG_SMP && !CONFIG_DEBUG_MUTEXES &&
	 !CONFIG_HAVE_DEFAULT_NO_SPIN_MUTEXES */

static __used noinline void __sched __mutex_unlock_slowpath(atomic_t *lock_count);

/***
 * mutex_unlock - release the mutex
 * @lock: the mutex to be released
 *
 * Unlock a mutex that has been locked by this task previously.
 *
 * This function must not be used in interrupt context. Unlocking
 * of a not locked mutex is not allowed.
 *
 * This function is similar to (but not equivalent to) up().
 */
void __sched mutex_unlock(struct mutex *lock)
{
	/*
	 * The unlocking fastpath is the 0->1 transition from 'locked'
	 * into 'unlocked' state:
	 */
#ifndef CONFIG_DEBUG_MUTEXES
	/*
	 * When debugging is enabled we must not clear the owner before time,
	 * the slow path will always be taken, and that clears the owner field
	 * after verifying that it was indeed current.
	 */
	mutex_clear_owner(lock);
#endif
	__mutex_fastpath_unlock(&lock->count, __mutex_unlock_slowpath);
}

EXPORT_SYMBOL(mutex_unlock);

/**
 * ww_mutex_unlock - release the w/w mutex
 * @lock: the mutex to be released
 *
 * Unlock a mutex that has been locked by this task previously with any of the
 * ww_mutex_lock* functions (with or without an acquire context). It is
 * forbidden to release the locks after releasing the acquire context.
 *
 * This function must not be used in interrupt context. Unlocking
 * of a unlocked mutex is not allowed.
 */
void __sched ww_mutex_unlock(struct ww_mutex *lock)
{
	/*
	 * The unlocking fastpath is the 0->1 transition from 'locked'
	 * into 'unlocked' state:
	 */
	if (lock->ctx) {
#ifdef CONFIG_DEBUG_MUTEXES
		DEBUG_LOCKS_WARN_ON(!lock->ctx->acquired);
#endif
		if (lock->ctx->acquired > 0)
			lock->ctx->acquired--;
		lock->ctx = NULL;
	}

#ifndef CONFIG_DEBUG_MUTEXES
	/*
	 * When debugging is enabled we must not clear the owner before time,
	 * the slow path will always be taken, and that clears the owner field
	 * after verifying that it was indeed current.
	 */
	mutex_clear_owner(&lock->base);
#endif
	__mutex_fastpath_unlock(&lock->base.count, __mutex_unlock_slowpath);
}
EXPORT_SYMBOL(ww_mutex_unlock);

static inline int __sched
__mutex_lock_check_stamp(struct mutex *lock, struct ww_acquire_ctx *ctx)
{
	struct ww_mutex *ww = container_of(lock, struct ww_mutex, base);
	struct ww_acquire_ctx *hold_ctx = ACCESS_ONCE(ww->ctx);

	if (!hold_ctx)
		return 0;

	if (unlikely(ctx == hold_ctx))
		return -EALREADY;

	if (ctx->stamp - hold_ctx->stamp <= LONG_MAX &&
	    (ctx->stamp != hold_ctx->stamp || ctx > hold_ctx)) {
#ifdef CONFIG_DEBUG_MUTEXES
		DEBUG_LOCKS_WARN_ON(ctx->contending_lock);
		ctx->contending_lock = ww;
#endif
		return -EDEADLK;
	}

	return 0;
}

static __always_inline void ww_mutex_lock_acquired(struct ww_mutex *ww,
						   struct ww_acquire_ctx *ww_ctx)
{
#ifdef CONFIG_DEBUG_MUTEXES
	/*
	 * If this WARN_ON triggers, you used ww_mutex_lock to acquire,
	 * but released with a normal mutex_unlock in this call.
	 *
	 * This should never happen, always use ww_mutex_unlock.
	 */
	DEBUG_LOCKS_WARN_ON(ww->ctx);

	/*
	 * Not quite done after calling ww_acquire_done() ?
	 */
	DEBUG_LOCKS_WARN_ON(ww_ctx->done_acquire);

	if (ww_ctx->contending_lock) {
		/*
		 * After -EDEADLK you tried to
		 * acquire a different ww_mutex? Bad!
		 */
		DEBUG_LOCKS_WARN_ON(ww_ctx->contending_lock != ww);

		/*
		 * You called ww_mutex_lock after receiving -EDEADLK,
		 * but 'forgot' to unlock everything else first?
		 */
		DEBUG_LOCKS_WARN_ON(ww_ctx->acquired > 0);
		ww_ctx->contending_lock = NULL;
	}

	/*
	 * Naughty, using a different class will lead to undefined behavior!
	 */
	DEBUG_LOCKS_WARN_ON(ww_ctx->ww_class != ww->ww_class);
#endif
	ww_ctx->acquired++;
}

/*
 * after acquiring lock with fastpath or when we lost out in contested
 * slowpath, set ctx and wake up any waiters so they can recheck.
 *
 * This function is never called when CONFIG_DEBUG_LOCK_ALLOC is set,
 * as the fastpath and opportunistic spinning are disabled in that case.
 */
static __always_inline void
ww_mutex_set_context_fastpath(struct ww_mutex *lock,
			       struct ww_acquire_ctx *ctx)
{
	unsigned long flags;
	struct mutex_waiter *cur;

	ww_mutex_lock_acquired(lock, ctx);

	lock->ctx = ctx;

	/*
	 * The lock->ctx update should be visible on all cores before
	 * the atomic read is done, otherwise contended waiters might be
	 * missed. The contended waiters will either see ww_ctx == NULL
	 * and keep spinning, or it will acquire wait_lock, add itself
	 * to waiter list and sleep.
	 */
	smp_mb(); /* ^^^ */

	/*
	 * Check if lock is contended, if not there is nobody to wake up
	 */
	if (likely(atomic_read(&lock->base.count) == 0))
		return;

	/*
	 * Uh oh, we raced in fastpath, wake up everyone in this case,
	 * so they can see the new lock->ctx.
	 */
	spin_lock_mutex(&lock->base.wait_lock, flags);
	mutex_list_for_each_entry(cur, &lock->base.wait_list, list) {
		debug_mutex_wake_waiter(&lock->base, cur);
		wake_up_process(cur->task);
	}
	spin_unlock_mutex(&lock->base.wait_lock, flags);
}

/*
 * Lock a mutex (possibly interruptible), slowpath:
 */
static __always_inline int __sched
__mutex_lock_common(struct mutex *lock, long state, unsigned int subclass,
		    struct lockdep_map *nest_lock, unsigned long ip,
		    struct ww_acquire_ctx *ww_ctx)
{
	struct task_struct *task = current;
	struct mutex_waiter waiter;
	unsigned long flags;
	int ret;

	preempt_disable();
	mutex_acquire_nest(&lock->dep_map, subclass, 0, nest_lock, ip);
#if defined(CONFIG_SMP) && !defined(CONFIG_DEBUG_MUTEXES) && \
    !defined(CONFIG_HAVE_DEFAULT_NO_SPIN_MUTEXES)
	/*
	 * Optimistic spinning.
	 *
	 * We try to spin for acquisition when we find that there are no
	 * pending waiters and the lock owner is currently running on a
	 * (different) CPU.
	 *
	 * The rationale is that if the lock owner is running, it is likely to
	 * release the lock soon.
	 *
	 * Since this needs the lock owner, and this mutex implementation
	 * doesn't track the owner atomically in the lock field, we need to
	 * track it non-atomically.
	 *
	 * We can't do this for DEBUG_MUTEXES because that relies on wait_lock
	 * to serialize everything.
	 *
	 * The mutex spinners are queued up using MCS lock so that only one
	 * spinner can compete for the mutex. However, if mutex spinning isn't
	 * going to happen, there is no point in going through the lock/unlock
	 * overhead.
	 */

	if (current->lock_depth >= 0)
		goto slowpath;	/* Don't spin if we own BKL */
	if (!osq_lock(lock, OSQ_LOCK(lock)))
		goto slowpath;
	for (;;) {
		struct thread_info *owner;

		/*
		 * If we own the BKL, then don't spin. The owner of the mutex
		 * might be waiting on us to release the BKL.
		 */
		if (current->lock_depth >= 0)
			break;

		if (!__builtin_constant_p(ww_ctx == NULL) && ww_ctx->acquired > 0) {
			struct ww_mutex *ww;

			ww = container_of(lock, struct ww_mutex, base);
			/*
			 * If ww->ctx is set the contents are undefined, only
			 * by acquiring wait_lock there is a guarantee that
			 * they are not invalid when reading.
			 *
			 * As such, when deadlock detection needs to be
			 * performed the optimistic spinning cannot be done.
			 */
			if (ACCESS_ONCE(ww->ctx))
				break;
		}

		/*
		 * If there's an owner, wait for it to either
		 * release the lock or go to sleep.
		 */
		owner = ACCESS_ONCE(lock->owner);
		if (owner && !mutex_spin_on_owner(lock, owner))
			break;

		if ((atomic_read(&lock->count) == 1) &&
		    (atomic_cmpxchg(&lock->count, 1, 0) == 1)) {
			lock_acquired(&lock->dep_map, ip);
			if (!__builtin_constant_p(ww_ctx == NULL)) {
				struct ww_mutex *ww;
				ww = container_of(lock, struct ww_mutex, base);

				ww_mutex_set_context_fastpath(ww, ww_ctx);
			}

			mutex_set_owner(lock);
			osq_unlock(OSQ_LOCK(lock));
			preempt_enable();
			return 0;
		}

		/*
		 * When there's no owner, we might have preempted between the
		 * owner acquiring the lock and setting the owner field. If
		 * we're an RT task that will live-lock because we won't let
		 * the owner complete.
		 */
		if (!owner && (need_resched() || rt_task(task)))
			break;

		/*
		 * The cpu_relax() call is a compiler barrier which forces
		 * everything in this loop to be re-loaded. We don't need
		 * memory barriers as we'll eventually observe the right
		 * values at the cost of a few extra spins.
		 */
		arch_mutex_cpu_relax();
	}
	osq_unlock(OSQ_LOCK(lock));
slowpath:
#endif
	spin_lock_mutex(&lock->wait_lock, flags);

	/* once more, can we acquire the lock? */
	if (MUTEX_SHOW_NO_WAITER(lock) && (atomic_xchg(&lock->count, 0) == 1))
		goto skip_wait;

	debug_mutex_lock_common(lock, &waiter);
	debug_mutex_add_waiter(lock, &waiter, task_thread_info(task));

	/* add waiting tasks to the end of the waitqueue (FIFO): */
	mutex_add_waiter(&waiter.list, &lock->wait_list);
	waiter.task = task;

	lock_contended(&lock->dep_map, ip);

	for (;;) {
		/*
		 * Lets try to take the lock again - this is needed even if
		 * we get here for the first time (shortly after failing to
		 * acquire the lock), to make sure that we get a wakeup once
		 * it's unlocked. Later on, if we sleep, this is the
		 * operation that gives us the lock. We xchg it to -1, so
		 * that when we release the lock, we properly wake up the
		 * other waiters:
		 */
		if (MUTEX_SHOW_NO_WAITER(lock) &&
		    (atomic_xchg(&lock->count, -1) == 1))
			break;

		/*
		 * got a signal? (This code gets eliminated in the
		 * TASK_UNINTERRUPTIBLE case.)
		 */
		if (unlikely(signal_pending_state(state, task))) {
			ret = -EINTR;
			goto err;
		}

		if (!__builtin_constant_p(ww_ctx == NULL) && ww_ctx->acquired > 0) {
			ret = __mutex_lock_check_stamp(lock, ww_ctx);
			if (ret)
				goto err;
		}

		__set_task_state(task, state);

		/* didnt get the lock, go to sleep: */
		spin_unlock_mutex(&lock->wait_lock, flags);
		preempt_enable_no_resched();
		schedule();
		preempt_disable();
		spin_lock_mutex(&lock->wait_lock, flags);
	}
	mutex_remove_waiter(lock, &waiter, current_thread_info());
	/* set it to 0 if there are no waiters left: */
	if (likely(MUTEX_LIST_EMPTY(&lock->wait_list)))
		atomic_set(&lock->count, 0);
	debug_mutex_free_waiter(&waiter);

skip_wait:
	/* got the lock - cleanup and rejoice! */
	lock_acquired(&lock->dep_map, ip);
	mutex_set_owner(lock);

	if (!__builtin_constant_p(ww_ctx == NULL)) {
		struct ww_mutex *ww = container_of(lock,
						      struct ww_mutex,
						      base);
		struct mutex_waiter *cur;

		/*
		 * This branch gets optimized out for the common case,
		 * and is only important for ww_mutex_lock.
		 */

		ww_mutex_lock_acquired(ww, ww_ctx);
		ww->ctx = ww_ctx;

		/*
		 * Give any possible sleeping processes the chance to wake up,
		 * so they can recheck if they have to back off.
		 */
		mutex_list_for_each_entry(cur, &lock->wait_list, list) {
			debug_mutex_wake_waiter(lock, cur);
			wake_up_process(cur->task);
		}
	}

	spin_unlock_mutex(&lock->wait_lock, flags);
	preempt_enable();

	return 0;

err:
	mutex_remove_waiter(lock, &waiter, task_thread_info(task));
	spin_unlock_mutex(&lock->wait_lock, flags);
	debug_mutex_free_waiter(&waiter);
	mutex_release(&lock->dep_map, 1, ip);
	preempt_enable();
	return ret;
}

#ifdef CONFIG_DEBUG_LOCK_ALLOC
void __sched
mutex_lock_nested(struct mutex *lock, unsigned int subclass)
{
	might_sleep();
	__mutex_lock_common(lock, TASK_UNINTERRUPTIBLE,
			    subclass, NULL, _RET_IP_, NULL);
}

EXPORT_SYMBOL_GPL(mutex_lock_nested);

void __sched
_mutex_lock_nest_lock(struct mutex *lock, struct lockdep_map *nest)
{
	might_sleep();
	__mutex_lock_common(lock, TASK_UNINTERRUPTIBLE,
			    0, nest, _RET_IP_, NULL);
}

EXPORT_SYMBOL_GPL(_mutex_lock_nest_lock);

int __sched
mutex_lock_killable_nested(struct mutex *lock, unsigned int subclass)
{
	might_sleep();
	return __mutex_lock_common(lock, TASK_KILLABLE,
				   subclass, NULL, _RET_IP_, NULL);
}
EXPORT_SYMBOL_GPL(mutex_lock_killable_nested);

int __sched
mutex_lock_interruptible_nested(struct mutex *lock, unsigned int subclass)
{
	might_sleep();
	return __mutex_lock_common(lock, TASK_INTERRUPTIBLE,
				   subclass, NULL, _RET_IP_, NULL);
}

EXPORT_SYMBOL_GPL(mutex_lock_interruptible_nested);

static inline int
ww_mutex_deadlock_injection(struct ww_mutex *lock, struct ww_acquire_ctx *ctx)
{
#ifdef CONFIG_DEBUG_WW_MUTEX_SLOWPATH
	unsigned tmp;

	if (ctx->deadlock_inject_countdown-- == 0) {
		tmp = ctx->deadlock_inject_interval;
		if (tmp > UINT_MAX/4)
			tmp = UINT_MAX;
		else
			tmp = tmp*2 + tmp + tmp/2;

		ctx->deadlock_inject_interval = tmp;
		ctx->deadlock_inject_countdown = tmp;
		ctx->contending_lock = lock;

		ww_mutex_unlock(lock);

		return -EDEADLK;
	}
#endif

	return 0;
}

int __sched
__ww_mutex_lock(struct ww_mutex *lock, struct ww_acquire_ctx *ctx)
{
	int ret;

	might_sleep();
	ret =  __mutex_lock_common(&lock->base, TASK_UNINTERRUPTIBLE,
				   0, &ctx->dep_map, _RET_IP_, ctx);
	if (!ret && ctx->acquired > 0)
		return ww_mutex_deadlock_injection(lock, ctx);

	return ret;
}
EXPORT_SYMBOL_GPL(__ww_mutex_lock);

int __sched
__ww_mutex_lock_interruptible(struct ww_mutex *lock, struct ww_acquire_ctx *ctx)
{
	int ret;

	might_sleep();
	ret = __mutex_lock_common(&lock->base, TASK_INTERRUPTIBLE,
				  0, &ctx->dep_map, _RET_IP_, ctx);

	if (!ret && ctx->acquired > 0)
		return ww_mutex_deadlock_injection(lock, ctx);

	return ret;
}
EXPORT_SYMBOL_GPL(__ww_mutex_lock_interruptible);

#endif

/*
 * Release the lock, slowpath:
 */
static inline void
__mutex_unlock_common_slowpath(atomic_t *lock_count, int nested)
{
	struct mutex *lock = container_of(lock_count, struct mutex, count);
	unsigned long flags;

	/*
	 * some architectures leave the lock unlocked in the fastpath failure
	 * case, others need to leave it locked. In the later case we have to
	 * unlock it here
	 */
	if (__mutex_slowpath_needs_to_unlock())
		atomic_set(&lock->count, 1);

	spin_lock_mutex(&lock->wait_lock, flags);
	mutex_release(&lock->dep_map, nested, _RET_IP_);
	debug_mutex_unlock(lock);

	if (!MUTEX_LIST_EMPTY(&lock->wait_list)) {
		/* get the first entry from the wait-list: */
		struct mutex_waiter *waiter =
				list_entry(mutex_waitlist_head(lock),
					   struct mutex_waiter, list);

		debug_mutex_wake_waiter(lock, waiter);

		wake_up_process(waiter->task);
	}

	spin_unlock_mutex(&lock->wait_lock, flags);
}

/*
 * Release the lock, slowpath:
 */
static __used noinline void
__mutex_unlock_slowpath(atomic_t *lock_count)
{
	__mutex_unlock_common_slowpath(lock_count, 1);
}

#ifndef CONFIG_DEBUG_LOCK_ALLOC
/*
 * Here come the less common (and hence less performance-critical) APIs:
 * mutex_lock_interruptible() and mutex_trylock().
 */
static noinline int __sched
__mutex_lock_killable_slowpath(struct mutex *lock);

static noinline int __sched
__mutex_lock_interruptible_slowpath(struct mutex *lock);

/***
 * mutex_lock_interruptible - acquire the mutex, interruptable
 * @lock: the mutex to be acquired
 *
 * Lock the mutex like mutex_lock(), and return 0 if the mutex has
 * been acquired or sleep until the mutex becomes available. If a
 * signal arrives while waiting for the lock then this function
 * returns -EINTR.
 *
 * This function is similar to (but not equivalent to) down_interruptible().
 */
int __sched mutex_lock_interruptible(struct mutex *lock)
{
	int ret;

	might_sleep();
	ret =  __mutex_fastpath_lock_retval(&lock->count);
	if (likely(!ret)) {
		mutex_set_owner(lock);
		return 0;
	} else
		return __mutex_lock_interruptible_slowpath(lock);
}

EXPORT_SYMBOL(mutex_lock_interruptible);

int __sched mutex_lock_killable(struct mutex *lock)
{
	int ret;

	might_sleep();
	ret = __mutex_fastpath_lock_retval(&lock->count);
	if (likely(!ret)) {
		mutex_set_owner(lock);
		return 0;
	} else
		return __mutex_lock_killable_slowpath(lock);
}
EXPORT_SYMBOL(mutex_lock_killable);

static __used noinline void __sched
__mutex_lock_slowpath(atomic_t *lock_count)
{
	struct mutex *lock = container_of(lock_count, struct mutex, count);

	__mutex_lock_common(lock, TASK_UNINTERRUPTIBLE, 0,
			    NULL, _RET_IP_, NULL);
}

static noinline int __sched
__mutex_lock_killable_slowpath(struct mutex *lock)
{
	return __mutex_lock_common(lock, TASK_KILLABLE, 0,
				   NULL, _RET_IP_, NULL);
}

static noinline int __sched
__mutex_lock_interruptible_slowpath(struct mutex *lock)
{
	return __mutex_lock_common(lock, TASK_INTERRUPTIBLE, 0,
				   NULL, _RET_IP_, NULL);
}

static noinline int __sched
__ww_mutex_lock_slowpath(struct ww_mutex *lock, struct ww_acquire_ctx *ctx)
{
	return __mutex_lock_common(&lock->base, TASK_UNINTERRUPTIBLE, 0,
				   NULL, _RET_IP_, ctx);
}

static noinline int __sched
__ww_mutex_lock_interruptible_slowpath(struct ww_mutex *lock,
					    struct ww_acquire_ctx *ctx)
{
	return __mutex_lock_common(&lock->base, TASK_INTERRUPTIBLE, 0,
				   NULL, _RET_IP_, ctx);
}

#endif

/*
 * Spinlock based trylock, we take the spinlock and check whether we
 * can get the lock:
 */
static inline int __mutex_trylock_slowpath(atomic_t *lock_count)
{
	struct mutex *lock = container_of(lock_count, struct mutex, count);
	unsigned long flags;
	int prev;

	spin_lock_mutex(&lock->wait_lock, flags);

	prev = atomic_xchg(&lock->count, -1);
	if (likely(prev == 1)) {
		mutex_set_owner(lock);
		mutex_acquire(&lock->dep_map, 0, 1, _RET_IP_);
	}

	/* Set it back to 0 if there are no waiters: */
	if (likely(MUTEX_LIST_EMPTY(&lock->wait_list)))
		atomic_set(&lock->count, 0);

	spin_unlock_mutex(&lock->wait_lock, flags);

	return prev == 1;
}

/***
 * mutex_trylock - try acquire the mutex, without waiting
 * @lock: the mutex to be acquired
 *
 * Try to acquire the mutex atomically. Returns 1 if the mutex
 * has been acquired successfully, and 0 on contention.
 *
 * NOTE: this function follows the spin_trylock() convention, so
 * it is negated to the down_trylock() return values! Be careful
 * about this when converting semaphore users to mutexes.
 *
 * This function must not be used in interrupt context. The
 * mutex must be released by the same task that acquired it.
 */
int __sched mutex_trylock(struct mutex *lock)
{
	int ret;

	ret = __mutex_fastpath_trylock(&lock->count, __mutex_trylock_slowpath);
	if (ret)
		mutex_set_owner(lock);

	return ret;
}
EXPORT_SYMBOL(mutex_trylock);

#ifndef CONFIG_DEBUG_LOCK_ALLOC
int __sched
__ww_mutex_lock(struct ww_mutex *lock, struct ww_acquire_ctx *ctx)
{
	int ret;

	might_sleep();

	ret = __mutex_fastpath_lock_retval(&lock->base.count);

	if (likely(!ret)) {
		ww_mutex_set_context_fastpath(lock, ctx);
		mutex_set_owner(&lock->base);
	} else
		ret = __ww_mutex_lock_slowpath(lock, ctx);
	return ret;
}
EXPORT_SYMBOL(__ww_mutex_lock);

int __sched
__ww_mutex_lock_interruptible(struct ww_mutex *lock, struct ww_acquire_ctx *ctx)
{
	int ret;

	might_sleep();

	ret = __mutex_fastpath_lock_retval(&lock->base.count);

	if (likely(!ret)) {
		ww_mutex_set_context_fastpath(lock, ctx);
		mutex_set_owner(&lock->base);
	} else
		ret = __ww_mutex_lock_interruptible_slowpath(lock, ctx);
	return ret;
}
EXPORT_SYMBOL(__ww_mutex_lock_interruptible);

#endif

/**
 * atomic_dec_and_mutex_lock - return holding mutex if we dec to 0
 * @cnt: the atomic which we are to dec
 * @lock: the mutex to return holding if we dec to 0
 *
 * return true and hold lock if we dec to 0, return false otherwise
 */
int atomic_dec_and_mutex_lock(atomic_t *cnt, struct mutex *lock)
{
	/* dec if we can't possibly hit 0 */
	if (atomic_add_unless(cnt, -1, 1))
		return 0;
	/* we might hit 0, so take the lock */
	mutex_lock(lock);
	if (!atomic_dec_and_test(cnt)) {
		/* when we actually did the dec, we didn't hit 0 */
		mutex_unlock(lock);
		return 0;
	}
	/* we hit 0, and we hold the lock */
	return 1;
}
EXPORT_SYMBOL(atomic_dec_and_mutex_lock);
