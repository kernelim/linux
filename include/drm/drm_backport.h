/*
 * Copyright (C) 2013 Red Hat
 *
 * This file is subject to the terms and conditions of the GNU General Public
 * License v2. See the file COPYING in the main directory of this archive for
 * more details.
 */

#ifndef DRM_BACKPORT_H_
#define DRM_BACKPORT_H_

/* config option was renamed upstream in d3f138106b4b40 .. add compat
 * glue so that we can use the new #define in drm code
 */
#ifdef CONFIG_DMAR
#  define CONFIG_INTEL_IOMMU 1
#endif

#include <linux/vmalloc.h>
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

/**
 * list_last_entry - get the last element from a list
 * @ptr:	the list head to take the element from.
 * @type:	the type of the struct this is embedded in.
 * @member:	the name of the list_struct within the struct.
 *
 * Note, that list is expected to be not empty.
 */
#define list_last_entry(ptr, type, member) \
	list_entry((ptr)->prev, type, member)

#define module_param_named_unsafe(name, value, type, perm)		\
	module_param_named(name, value, type, perm)

static inline u64 ktime_get_raw_ns(void)
{
	struct timespec now;
	getrawmonotonic(&now);
	return timespec_to_ns(&now);
}

/**
 * ktime_mono_to_real - Convert monotonic time to clock realtime
 */
static inline ktime_t ktime_mono_to_real(ktime_t mono)
{
	return ktime_sub(mono, ktime_get_monotonic_offset());
}

static inline unsigned long vm_mmap(struct file *file, unsigned long addr,
	unsigned long len, unsigned long prot,
	unsigned long flag, unsigned long offset)
{
	unsigned long ret;
	down_write(&current->mm->mmap_sem);
	ret = do_mmap(file, addr, len, prot, flag, offset);
	up_write(&current->mm->mmap_sem);
	return ret;
}

static inline int kref_put_mutex(struct kref *kref,
				 void (*release)(struct kref *kref),
				 struct mutex *lock)
{
	WARN_ON(release == NULL);
	if (unlikely(!atomic_add_unless(&kref->refcount, -1, 1))) {
		mutex_lock(lock);
		if (unlikely(!atomic_dec_and_test(&kref->refcount))) {
			mutex_unlock(lock);
			return 0;
		}
		release(kref);
		return 1;
	}
	return 0;
}


typedef struct {
	uid_t val;
} kuid_t;

static inline uid_t from_kuid_munged(struct user_namespace *targ, kuid_t kuid)
{
	return kuid.val;
}

static inline struct user_namespace *seq_user_ns(struct seq_file *seq)
{
	return NULL;
}

static const char power_group_name[] = "power";

#include <linux/mm.h>

/*
 * This struct is used to pass information from page reclaim to the shrinkers.
 * We consolidate the values for easier extention later.
 *
 * The 'gfpmask' refers to the allocation we are currently trying to
 * fulfil.
 */
struct shrink_control {
	gfp_t gfp_mask;

	/*
	 * How many objects scan_objects should scan and try to reclaim.
	 * This is reset before every call, so it is safe for callees
	 * to modify.
	 */
	unsigned long nr_to_scan;

	/* shrink from these nodes */
	nodemask_t nodes_to_scan;
	/* current node being shrunk (for NUMA aware shrinkers) */
	int nid;
};

#define SHRINK_STOP (~0UL)
/*
 * A callback you can register to apply pressure to ageable caches.
 *
 * @count_objects should return the number of freeable items in the cache. If
 * there are no objects to free or the number of freeable items cannot be
 * determined, it should return 0. No deadlock checks should be done during the
 * count callback - the shrinker relies on aggregating scan counts that couldn't
 * be executed due to potential deadlocks to be run at a later call when the
 * deadlock condition is no longer pending.
 *
 * @scan_objects will only be called if @count_objects returned a non-zero
 * value for the number of freeable objects. The callout should scan the cache
 * and attempt to free items from the cache. It should then return the number
 * of objects freed during the scan, or SHRINK_STOP if progress cannot be made
 * due to potential deadlocks. If SHRINK_STOP is returned, then no further
 * attempts to call the @scan_objects will be made from the current reclaim
 * context.
 *
 * @flags determine the shrinker abilities, like numa awareness
 */
struct shrinker2 {
	unsigned long (*count_objects)(struct shrinker2 *,
				       struct shrink_control *sc);
	unsigned long (*scan_objects)(struct shrinker2 *,
				      struct shrink_control *sc);

	int seeks;	/* seeks to recreate an obj */
	long batch;	/* reclaim batch size, 0 = default */
	unsigned long flags;

	/* These are for internal use */
	struct list_head list;
	/* objs pending delete, per node */
	atomic_long_t *nr_deferred;

	/* compat: */
	struct shrinker compat;
};
void register_shrinker2(struct shrinker2 *shrinker);
void unregister_shrinker2(struct shrinker2 *shrinker);

#define shrinker            shrinker2
#define register_shrinker   register_shrinker2
#define unregister_shrinker unregister_shrinker2

#define VM_DONTDUMP VM_RESERVED   /* not entirely true, but works for drm usages */

static inline void pm_runtime_mark_last_busy(struct device *dev) {}
static inline void pm_runtime_set_autosuspend_delay(struct device *dev, int delay) {}
static inline void pm_runtime_use_autosuspend(struct device *dev) {}
static inline int pm_runtime_put_autosuspend(struct device *dev) { return 0; }
static inline int pm_runtime_autosuspend(struct device *dev) { return 0; }

struct dev_pm_domain {
	struct dev_pm_ops	ops;
	void (*detach)(struct device *dev, bool power_off);
};

#include <linux/vga_switcheroo.h>
static inline void vga_switcheroo_set_dynamic_switch(struct pci_dev *pdev, enum vga_switcheroo_state dynamic) {}
static inline int vga_switcheroo_init_domain_pm_ops(struct device *dev, struct dev_pm_domain *domain) { return 0; }
static inline void vga_switcheroo_fini_domain_pm_ops(struct device *dev) {}


/* redirect things to our own idr/ida: */
#define __IDR_H__
#include <linux/idr2.h>
#define idr                idr2
#define idr_find_slowpath  idr2_find_slowpath
#define idr_preload        idr2_preload
#define idr_alloc          idr2_alloc
#define idr_alloc_cyclic   idr2_alloc_cyclic
#define idr_for_each       idr2_for_each
#define idr_get_next       idr2_get_next
#define idr_replace        idr2_replace
#define idr_remove         idr2_remove
#define idr_destroy        idr2_destroy
#define idr_init           idr2_init
#define idr_is_empty       idr2_is_empty
#define idr_preload_end    idr2_preload_end
#define idr_find           idr2_find
#define idr_for_each_entry idr2_for_each_entry
#define ida                ida2
#define ida_pre_get        ida2_pre_get
#define ida_get_new_above  ida2_get_new_above
#define ida_remove         ida2_remove
#define ida_destroy        ida2_destroy
#define ida_init           ida2_init
#define ida_simple_get     ida2_simple_get
#define ida_simple_remove  ida2_simple_remove
#define ida_get_new        ida2_get_new

static inline unsigned long get_num_physpages(void)
{
	return num_physpages;
}

char *simple_dname(struct dentry *dentry, char *buffer, int buflen);
struct inode *alloc_anon_inode(struct super_block *mnt_sb);

/* TODO backport! */

//#define BUILD_BUG_ON(condition) ((void)sizeof(char[1 - 2*!!(condition)]))
#define BUILD_BUG_ON_MSG(cond, msg)
#define BUILD_BUG()

static inline void __iomem *pci_platform_rom(struct pci_dev *pdev, size_t *size)
{
	return NULL;
}

#define module_param_unsafe(name, type, perm) module_param(name, type, perm)

#define DIV_ROUND_CLOSEST_ULL(ll, d)    \
 ({ unsigned long long _tmp = (ll)+(d)/2; do_div(_tmp, d); _tmp; })

#define atomic_or(mask, v) atomic_set_mask(mask, v)

int __init drm_backport_init(void);
void __exit drm_backport_exit(void);


#undef pr_fmt

#endif /* DRM_BACKPORT_H_ */
