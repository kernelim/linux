/* SPDX-License-Identifier: GPL-2.0 */

/*
 * Compatibility shim to avoid backporting the following commits:
 *
 * 93065ac753e4 ("mm, oom: distinguish blockable mode for mmu notifiers")
 * 5d6527a784f7 ("mm/mmu_notifier: use structure for invalidate_range_start/end callback")
 * ac46d4f3c432 ("mm/mmu_notifier: use structure for invalidate_range_start/end calls v2")
 *
 * If modifying these, please keep in mind that the RHEL8 kernel does not
 * currently support non-blockable mmu_notifier_ranges. This means that we
 * need to ensure that ALL ranges passed to callbacks are blockable.
 */

#ifndef __RH_DRM_BACKPORT_MMU_NOTIFIER_H__
#define __RH_DRM_BACKPORT_MMU_NOTIFIER_H__

#include_next <linux/mmu_notifier.h>

#ifdef RH_DRM_BACKPORT
#ifdef CONFIG_MMU_NOTIFIER

struct __rh_drm_mmu_notifier;
struct __rh_drm_mmu_notifier_ops {
	/*
	 * Flags to specify behavior of callbacks for this MMU notifier.
	 * Used to determine which context an operation may be called.
	 *
	 * MMU_INVALIDATE_DOES_NOT_BLOCK: invalidate_range_* callbacks do not
	 *	block
	 */
	int flags;

	/*
	 * Called either by mmu_notifier_unregister or when the mm is
	 * being destroyed by exit_mmap, always before all pages are
	 * freed. This can run concurrently with other mmu notifier
	 * methods (the ones invoked outside the mm context) and it
	 * should tear down all secondary mmu mappings and freeze the
	 * secondary mmu. If this method isn't implemented you've to
	 * be sure that nothing could possibly write to the pages
	 * through the secondary mmu by the time the last thread with
	 * tsk->mm == mm exits.
	 *
	 * As side note: the pages freed after ->release returns could
	 * be immediately reallocated by the gart at an alias physical
	 * address with a different cache model, so if ->release isn't
	 * implemented because all _software_ driven memory accesses
	 * through the secondary mmu are terminated by the time the
	 * last thread of this mm quits, you've also to be sure that
	 * speculative _hardware_ operations can't allocate dirty
	 * cachelines in the cpu that could not be snooped and made
	 * coherent with the other read and write operations happening
	 * through the gart alias address, so leading to memory
	 * corruption.
	 */
	void (*release)(struct __rh_drm_mmu_notifier *mn,
			struct mm_struct *mm);

	/*
	 * clear_flush_young is called after the VM is
	 * test-and-clearing the young/accessed bitflag in the
	 * pte. This way the VM will provide proper aging to the
	 * accesses to the page through the secondary MMUs and not
	 * only to the ones through the Linux pte.
	 * Start-end is necessary in case the secondary MMU is mapping the page
	 * at a smaller granularity than the primary MMU.
	 */
	int (*clear_flush_young)(struct __rh_drm_mmu_notifier *mn,
				 struct mm_struct *mm,
				 unsigned long start,
				 unsigned long end);

	/*
	 * clear_young is a lightweight version of clear_flush_young. Like the
	 * latter, it is supposed to test-and-clear the young/accessed bitflag
	 * in the secondary pte, but it may omit flushing the secondary tlb.
	 */
	int (*clear_young)(struct __rh_drm_mmu_notifier *mn,
			   struct mm_struct *mm,
			   unsigned long start,
			   unsigned long end);

	/*
	 * test_young is called to check the young/accessed bitflag in
	 * the secondary pte. This is used to know if the page is
	 * frequently used without actually clearing the flag or tearing
	 * down the secondary mapping on the page.
	 */
	int (*test_young)(struct __rh_drm_mmu_notifier *mn,
			  struct mm_struct *mm,
			  unsigned long address);

	/*
	 * change_pte is called in cases that pte mapping to page is changed:
	 * for example, when ksm remaps pte to point to a new shared page.
	 */
	void (*change_pte)(struct __rh_drm_mmu_notifier *mn,
			   struct mm_struct *mm,
			   unsigned long address,
			   pte_t pte);

	/*
	 * invalidate_range_start() and invalidate_range_end() must be
	 * paired and are called only when the mmap_sem and/or the
	 * locks protecting the reverse maps are held. If the subsystem
	 * can't guarantee that no additional references are taken to
	 * the pages in the range, it has to implement the
	 * invalidate_range() notifier to remove any references taken
	 * after invalidate_range_start().
	 *
	 * Invalidation of multiple concurrent ranges may be
	 * optionally permitted by the driver. Either way the
	 * establishment of sptes is forbidden in the range passed to
	 * invalidate_range_begin/end for the whole duration of the
	 * invalidate_range_begin/end critical section.
	 *
	 * invalidate_range_start() is called when all pages in the
	 * range are still mapped and have at least a refcount of one.
	 *
	 * invalidate_range_end() is called when all pages in the
	 * range have been unmapped and the pages have been freed by
	 * the VM.
	 *
	 * The VM will remove the page table entries and potentially
	 * the page between invalidate_range_start() and
	 * invalidate_range_end(). If the page must not be freed
	 * because of pending I/O or other circumstances then the
	 * invalidate_range_start() callback (or the initial mapping
	 * by the driver) must make sure that the refcount is kept
	 * elevated.
	 *
	 * If the driver increases the refcount when the pages are
	 * initially mapped into an address space then either
	 * invalidate_range_start() or invalidate_range_end() may
	 * decrease the refcount. If the refcount is decreased on
	 * invalidate_range_start() then the VM can free pages as page
	 * table entries are removed.  If the refcount is only
	 * droppped on invalidate_range_end() then the driver itself
	 * will drop the last refcount but it must take care to flush
	 * any secondary tlb before doing the final free on the
	 * page. Pages will no longer be referenced by the linux
	 * address space but may still be referenced by sptes until
	 * the last refcount is dropped.
	 *
	 * If blockable argument is set to false then the callback cannot
	 * sleep and has to return with -EAGAIN. 0 should be returned
	 * otherwise. Please note that if invalidate_range_start approves
	 * a non-blocking behavior then the same applies to
	 * invalidate_range_end.
	 *
	 */
	int (*invalidate_range_start)(struct __rh_drm_mmu_notifier *mn,
				      const struct mmu_notifier_range *range);
	void (*invalidate_range_end)(struct __rh_drm_mmu_notifier *mn,
				     const struct mmu_notifier_range *range);

	/*
	 * invalidate_range() is either called between
	 * invalidate_range_start() and invalidate_range_end() when the
	 * VM has to free pages that where unmapped, but before the
	 * pages are actually freed, or outside of _start()/_end() when
	 * a (remote) TLB is necessary.
	 *
	 * If invalidate_range() is used to manage a non-CPU TLB with
	 * shared page-tables, it not necessary to implement the
	 * invalidate_range_start()/end() notifiers, as
	 * invalidate_range() alread catches the points in time when an
	 * external TLB range needs to be flushed. For more in depth
	 * discussion on this see Documentation/vm/mmu_notifier.rst
	 *
	 * Note that this function might be called with just a sub-range
	 * of what was passed to invalidate_range_start()/end(), if
	 * called between those functions.
	 */
	void (*invalidate_range)(struct __rh_drm_mmu_notifier *mn,
				 struct mm_struct *mm,
				 unsigned long start, unsigned long end);

	/*
	 * These callbacks are used with the get/put interface to manage the
	 * lifetime of the mmu_notifier memory. alloc_notifier() returns a new
	 * notifier for use with the mm.
	 *
	 * free_notifier() is only called after the mmu_notifier has been
	 * fully put, calls to any ops callback are prevented and no ops
	 * callbacks are currently running. It is called from a SRCU callback
	 * and cannot sleep.
	 */
	struct mmu_notifier *(*alloc_notifier)(struct mm_struct *mm);
	void (*free_notifier)(struct __rh_drm_mmu_notifier *subscription);

};

struct __rh_drm_mmu_notifier {
	struct mmu_notifier base;
	struct mmu_notifier_ops base_ops;
	const struct __rh_drm_mmu_notifier_ops *ops;
};

extern int
__rh_drm_mmu_notifier_register(struct __rh_drm_mmu_notifier *mn,
			       struct mm_struct *mm,
			       int (*orig_func)(struct mmu_notifier *,
						struct mm_struct *));

static inline void
__rh_drm_mmu_notifier_unregister(struct __rh_drm_mmu_notifier *mn,
				 struct mm_struct *mm,
				 void (*orig_func)(struct mmu_notifier *,
						   struct mm_struct *))
{
	orig_func(&mn->base, mm);
}

extern void __rh_drm_mmu_notifier_put(struct __rh_drm_mmu_notifier *mn);

static inline bool
mmu_notifier_range_blockable(const struct mmu_notifier_range *range)
{
	return true;
}

#define mmu_notifier     __rh_drm_mmu_notifier
#define mmu_notifier_ops __rh_drm_mmu_notifier_ops

#define mmu_notifier_register(mn, mm) \
	__rh_drm_mmu_notifier_register(mn, mm, mmu_notifier_register)
#define __mmu_notifier_register(mn, mm) \
	__rh_drm_mmu_notifier_register(mn, mm, __mmu_notifier_register)
#define mmu_notifier_unregister(mn, mm) \
	__rh_drm_mmu_notifier_unregister(mn, mm, mmu_notifier_unregister)
#define mmu_notifier_unregister_no_release(mn, mm) \
	__rh_drm_mmu_notifier_unregister(mn, mm, \
					 mmu_notifier_unregister_no_release)
#define mmu_notifier_put(mn) \
	__rh_drm_mmu_notifier_put(mn)

#endif /* CONFIG_MMU_NOTIFIER */
#endif /* RH_DRM_BACKPORT */
#endif /* !__RH_DRM_BACKPORT_MMU_NOTIFIER_H__ */
