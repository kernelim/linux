/*
 * Mutexes: blocking mutual exclusion locks
 *
 * started by Ingo Molnar:
 *
 *  Copyright (C) 2004, 2005, 2006 Red Hat, Inc., Ingo Molnar <mingo@redhat.com>
 *
 * This file contains mutex debugging related internal prototypes, for the
 * !CONFIG_DEBUG_MUTEXES case. Most of them are NOPs:
 */

#define spin_lock_mutex(lock, flags) \
		do { spin_lock(lock); (void)(flags); } while (0)
#define spin_unlock_mutex(lock, flags) \
		do { spin_unlock(lock); (void)(flags); } while (0)
#if defined(CONFIG_SMP) && !defined(CONFIG_DEBUG_MUTEXES) && \
    !defined(CONFIG_HAVE_DEFAULT_NO_SPIN_MUTEXES)
/*
 * If CONFIG_MUTEX_SPIN_ON_OWNER and CONFIG_USE_MCS_SPIN_WAIT_QUEUE are
 * enabled, the content of the double pointers in wait_list will be
 * recasted as:
 * wait_list.next - A pointer to the list of waiting tasks
 * wait_list.prev - A pointer to the tail of the MCS node linked list
 *		    (mspin_lock)
 *
 * In other words, the dual-pointer list_head structure in mutex is reduced
 * to a single pointer to make room for a pointer to the mspin_node structure.
 * The single pointer (.next) now points to a circular doubly-linked list.
 * The list_empty() macro will still works with the modified interpretation.
 */

/**
 * mutex_add_waiter - add a waiter to the end of the list
 * @waiter: 	the waiter to be added
 * @list:	the list head pointer
 */
static inline void
mutex_add_waiter(struct list_head *waiter, struct list_head **list)
{
	if (MUTEX_LIST_EMPTY(list)) {
		*list        = waiter;
		waiter->next = waiter;
		waiter->prev = waiter;
	} else {
		list_add_tail(waiter, *list);
	}
}
#define mutex_waitlist_head(lock)	(lock)->wait_list
#define mutex_remove_waiter(lock, waiter, ti) \
		__mutex_remove_waiter(lock, (struct list_head *)waiter)

/**
 * __mutex_remove_waiter - remove a waiter from the list
 * @mutex: 	the mutex data structure pointer
 * @waiter:	the waiter list_head structure pointer
 */
static inline void
__mutex_remove_waiter(struct mutex *lock, struct list_head *waiter)
{
	if (waiter->next == waiter)
		/*
		 * Last element in the list, mark the wait list empty
		 */
		lock->wait_list = (struct list_head *)&lock->wait_list;
	else {
		/*
		 * If the element pointed to by wait_list is to be removed,
		 * wait_list will have to point to the next one in queue.
		 */
		if (lock->wait_list == waiter)
			lock->wait_list = waiter->next;
		__list_del(waiter->prev, waiter->next);
	}
}

#else
#define mutex_add_waiter(waiter, list)	list_add_tail(waiter, list)
#define mutex_waitlist_head(lock)	(lock)->wait_list.next
#define mutex_remove_waiter(lock, waiter, ti) \
		__list_del((waiter)->list.prev, (waiter)->list.next)
#endif

#ifdef CONFIG_SMP
static inline void mutex_set_owner(struct mutex *lock)
{
	lock->owner = current_thread_info();
}

static inline void mutex_clear_owner(struct mutex *lock)
{
	lock->owner = NULL;
}
#else
static inline void mutex_set_owner(struct mutex *lock)
{
}

static inline void mutex_clear_owner(struct mutex *lock)
{
}
#endif

#define debug_mutex_wake_waiter(lock, waiter)		do { } while (0)
#define debug_mutex_free_waiter(waiter)			do { } while (0)
#define debug_mutex_add_waiter(lock, waiter, ti)	do { } while (0)
#define debug_mutex_unlock(lock)			do { } while (0)
#define debug_mutex_init(lock, name, key)		do { } while (0)

static inline void
debug_mutex_lock_common(struct mutex *lock, struct mutex_waiter *waiter)
{
}
