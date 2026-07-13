// SPDX-License-Identifier: GPL-2.0
/*
 * Helpers for IOMMU drivers implementing SVA
 */
#include <linux/mutex.h>
#include <linux/sched/mm.h>
#include <linux/spinlock.h>
#include <linux/atomic.h>
#include <linux/list.h>
#include <linux/rcupdate.h>
#include <linux/rculist.h>
#include <linux/slab.h>
#include <linux/mmu_notifier.h>
#include <linux/iommu.h>

#include "iommu-sva-lib.h"

static DEFINE_MUTEX(iommu_sva_lock);
static DECLARE_IOASID_SET(iommu_sva_pasid);

/**
 * iommu_sva_alloc_pasid - Allocate a PASID for the mm
 * @mm: the mm
 * @min: minimum PASID value (inclusive)
 * @max: maximum PASID value (inclusive)
 *
 * Try to allocate a PASID for this mm, or take a reference to the existing one
 * provided it fits within the [@min, @max] range. On success the PASID is
 * available in mm->pasid and will be available for the lifetime of the mm.
 *
 * Returns 0 on success and < 0 on error.
 */
int iommu_sva_alloc_pasid(struct mm_struct *mm, ioasid_t min, ioasid_t max)
{
	int ret = 0;
	ioasid_t pasid;

	if (min == INVALID_IOASID || max == INVALID_IOASID ||
	    min == 0 || max < min)
		return -EINVAL;

	mutex_lock(&iommu_sva_lock);
	/* Is a PASID already associated with this mm? */
	if (pasid_valid(mm->pasid)) {
		if (mm->pasid < min || mm->pasid >= max)
			ret = -EOVERFLOW;
		goto out;
	}

	pasid = ioasid_alloc(&iommu_sva_pasid, min, max, mm);
	if (!pasid_valid(pasid))
		ret = -ENOMEM;
	else
		mm_pasid_set(mm, pasid);
out:
	mutex_unlock(&iommu_sva_lock);
	return ret;
}
EXPORT_SYMBOL_GPL(iommu_sva_alloc_pasid);

/* ioasid_find getter() requires a void * argument */
static bool __mmget_not_zero(void *mm)
{
	return mmget_not_zero(mm);
}

/**
 * iommu_sva_find() - Find mm associated to the given PASID
 * @pasid: Process Address Space ID assigned to the mm
 *
 * On success a reference to the mm is taken, and must be released with mmput().
 *
 * Returns the mm corresponding to this PASID, or an error if not found.
 */
struct mm_struct *iommu_sva_find(ioasid_t pasid)
{
	return ioasid_find(&iommu_sva_pasid, pasid, __mmget_not_zero);
}
EXPORT_SYMBOL_GPL(iommu_sva_find);

/*
 * Track mm_structs with active SVA bindings so we can flush IOMMU
 * cached translations when kernel page table pages are freed.
 */
struct sva_mm {
	struct mm_struct *mm;
	struct list_head list;
	struct rcu_head rcu;
	int refcount;
};

static DEFINE_SPINLOCK(sva_mm_lock);
static LIST_HEAD(sva_mm_list);
static atomic_t sva_mm_count = ATOMIC_INIT(0);

/**
 * iommu_sva_track_mm - Start tracking an mm for kernel PT change notification
 * @mm: the mm_struct to track
 *
 * Called by IOMMU drivers when SVA is bound for this mm.  If the mm is
 * already tracked, increments the refcount.  Otherwise allocates a new
 * tracking entry.  The mm's mmu_notifier chain must already include the
 * IOMMU driver's invalidate_range callback (registered during SVA bind).
 *
 * Returns 0 on success, -ENOMEM on allocation failure.
 */
int iommu_sva_track_mm(struct mm_struct *mm)
{
	struct sva_mm *smm;
	unsigned long flags;

	spin_lock_irqsave(&sva_mm_lock, flags);
	list_for_each_entry(smm, &sva_mm_list, list) {
		if (smm->mm == mm) {
			smm->refcount++;
			spin_unlock_irqrestore(&sva_mm_lock, flags);
			return 0;
		}
	}
	spin_unlock_irqrestore(&sva_mm_lock, flags);

	smm = kzalloc(sizeof(*smm), GFP_KERNEL);
	if (WARN_ON(!smm))
		return -ENOMEM;

	smm->mm = mm;
	smm->refcount = 1;

	spin_lock_irqsave(&sva_mm_lock, flags);
	{
		struct sva_mm *existing;

		list_for_each_entry(existing, &sva_mm_list, list) {
			if (existing->mm == mm) {
				existing->refcount++;
				spin_unlock_irqrestore(&sva_mm_lock, flags);
				kfree(smm);
				return 0;
			}
		}
	}
	list_add_rcu(&smm->list, &sva_mm_list);
	atomic_inc(&sva_mm_count);
	spin_unlock_irqrestore(&sva_mm_lock, flags);

	return 0;
}
EXPORT_SYMBOL_GPL(iommu_sva_track_mm);

/**
 * iommu_sva_untrack_mm - Stop tracking an mm for kernel PT change notification
 * @mm: the mm_struct to untrack
 *
 * Called by IOMMU drivers when SVA is unbound for this mm.  Decrements
 * the refcount and removes the tracking entry when it reaches zero.
 */
void iommu_sva_untrack_mm(struct mm_struct *mm)
{
	struct sva_mm *smm;
	unsigned long flags;

	spin_lock_irqsave(&sva_mm_lock, flags);
	list_for_each_entry(smm, &sva_mm_list, list) {
		if (smm->mm == mm) {
			if (--smm->refcount == 0) {
				list_del_rcu(&smm->list);
				atomic_dec(&sva_mm_count);
				spin_unlock_irqrestore(&sva_mm_lock, flags);
				kfree_rcu(smm, rcu);
				return;
			}
			spin_unlock_irqrestore(&sva_mm_lock, flags);
			return;
		}
	}
	spin_unlock_irqrestore(&sva_mm_lock, flags);
	WARN(1, "iommu_sva_untrack_mm: mm %px not found\n", mm);
}
EXPORT_SYMBOL_GPL(iommu_sva_untrack_mm);

/**
 * iommu_sva_invalidate_kva_range - Flush IOMMU caches before kernel PT free
 * @start: Start of kernel virtual address range
 * @end: End of kernel virtual address range
 *
 * Called from x86 mm code before freeing kernel page table pages.
 * Iterates all tracked SVA-bound mm_structs and calls
 * mmu_notifier_invalidate_range() for each, triggering IOTLB flushes
 * via the drivers' invalidate_range callbacks.
 *
 * Fast path: atomic_read() returns 0 when no SVA is active.
 */
void iommu_sva_invalidate_kva_range(unsigned long start, unsigned long end)
{
	struct sva_mm *smm;

	if (!atomic_read(&sva_mm_count))
		return;

	rcu_read_lock();
	list_for_each_entry_rcu(smm, &sva_mm_list, list) {
		if (mmget_not_zero(smm->mm)) {
			mmu_notifier_invalidate_range(smm->mm, start, end);
			mmput_async(smm->mm);
		}
	}
	rcu_read_unlock();
}
