// SPDX-License-Identifier: GPL-2.0
/*
 * Helpers for IOMMU drivers implementing SVA
 */
#include <linux/mmu_context.h>
#include <linux/mutex.h>
#include <linux/sched/mm.h>
#include <linux/iommu.h>
#include <linux/spinlock.h>
#include <linux/atomic.h>
#include <linux/list.h>
#include <linux/rcupdate.h>
#include <linux/rculist.h>
#include <linux/slab.h>
#include <linux/mmu_notifier.h>

#include "iommu-priv.h"

static DEFINE_MUTEX(iommu_sva_lock);
static struct iommu_domain *iommu_sva_domain_alloc(struct device *dev,
						   struct mm_struct *mm);
static int iommu_sva_track_mm(struct mm_struct *mm);
static void iommu_sva_untrack_mm(struct mm_struct *mm);

/* Allocate a PASID for the mm within range (inclusive) */
static struct iommu_mm_data *iommu_alloc_mm_data(struct mm_struct *mm, struct device *dev)
{
	struct iommu_mm_data *iommu_mm;
	ioasid_t pasid;

	lockdep_assert_held(&iommu_sva_lock);

	if (!arch_pgtable_dma_compat(mm))
		return ERR_PTR(-EBUSY);

	iommu_mm = mm->iommu_mm;
	/* Is a PASID already associated with this mm? */
	if (iommu_mm) {
		if (iommu_mm->pasid >= dev->iommu->max_pasids)
			return ERR_PTR(-EOVERFLOW);
		return iommu_mm;
	}

	iommu_mm = kzalloc(sizeof(struct iommu_mm_data), GFP_KERNEL);
	if (!iommu_mm)
		return ERR_PTR(-ENOMEM);

	pasid = iommu_alloc_global_pasid(dev);
	if (pasid == IOMMU_PASID_INVALID) {
		kfree(iommu_mm);
		return ERR_PTR(-ENOSPC);
	}
	iommu_mm->pasid = pasid;
	INIT_LIST_HEAD(&iommu_mm->sva_domains);
	/*
	 * Make sure the write to mm->iommu_mm is not reordered in front of
	 * initialization to iommu_mm fields. If it does, readers may see a
	 * valid iommu_mm with uninitialized values.
	 */
	smp_store_release(&mm->iommu_mm, iommu_mm);
	return iommu_mm;
}

/**
 * iommu_sva_bind_device() - Bind a process address space to a device
 * @dev: the device
 * @mm: the mm to bind, caller must hold a reference to mm_users
 *
 * Create a bond between device and address space, allowing the device to
 * access the mm using the PASID returned by iommu_sva_get_pasid(). If a
 * bond already exists between @device and @mm, an additional internal
 * reference is taken. Caller must call iommu_sva_unbind_device()
 * to release each reference.
 *
 * On error, returns an ERR_PTR value.
 */
struct iommu_sva *iommu_sva_bind_device(struct device *dev, struct mm_struct *mm)
{
	struct iommu_group *group = dev->iommu_group;
	struct iommu_attach_handle *attach_handle;
	struct iommu_mm_data *iommu_mm;
	struct iommu_domain *domain;
	struct iommu_sva *handle;
	int ret;

	if (!group)
		return ERR_PTR(-ENODEV);

	mutex_lock(&iommu_sva_lock);

	/* Allocate mm->pasid if necessary. */
	iommu_mm = iommu_alloc_mm_data(mm, dev);
	if (IS_ERR(iommu_mm)) {
		ret = PTR_ERR(iommu_mm);
		goto out_unlock;
	}

	/* A bond already exists, just take a reference`. */
	attach_handle = iommu_attach_handle_get(group, iommu_mm->pasid, IOMMU_DOMAIN_SVA);
	if (!IS_ERR(attach_handle)) {
		handle = container_of(attach_handle, struct iommu_sva, handle);
		if (attach_handle->domain->mm != mm) {
			ret = -EBUSY;
			goto out_unlock;
		}
		refcount_inc(&handle->users);
		mutex_unlock(&iommu_sva_lock);
		return handle;
	}

	if (PTR_ERR(attach_handle) != -ENOENT) {
		ret = PTR_ERR(attach_handle);
		goto out_unlock;
	}

	handle = kzalloc(sizeof(*handle), GFP_KERNEL);
	if (!handle) {
		ret = -ENOMEM;
		goto out_unlock;
	}

	/* Search for an existing domain. */
	list_for_each_entry(domain, &mm->iommu_mm->sva_domains, next) {
		ret = iommu_attach_device_pasid(domain, dev, iommu_mm->pasid,
						&handle->handle);
		if (!ret) {
			domain->users++;
			goto out;
		}
	}

	/* Allocate a new domain and set it on device pasid. */
	domain = iommu_sva_domain_alloc(dev, mm);
	if (IS_ERR(domain)) {
		ret = PTR_ERR(domain);
		goto out_free_handle;
	}

	ret = iommu_attach_device_pasid(domain, dev, iommu_mm->pasid,
					&handle->handle);
	if (ret)
		goto out_free_domain;
	domain->users = 1;
	list_add(&domain->next, &mm->iommu_mm->sva_domains);

out:
	refcount_set(&handle->users, 1);
	ret = iommu_sva_track_mm(mm);
	if (ret)
		goto out_unwind;
	mutex_unlock(&iommu_sva_lock);
	handle->dev = dev;
	return handle;

out_unwind:
	iommu_detach_device_pasid(domain, dev, iommu_mm->pasid);
	if (--domain->users == 0) {
		list_del(&domain->next);
		iommu_domain_free(domain);
	}
	goto out_free_handle;
out_free_domain:
	iommu_domain_free(domain);
out_free_handle:
	kfree(handle);
out_unlock:
	mutex_unlock(&iommu_sva_lock);
	return ERR_PTR(ret);
}
EXPORT_SYMBOL_GPL(iommu_sva_bind_device);

/**
 * iommu_sva_unbind_device() - Remove a bond created with iommu_sva_bind_device
 * @handle: the handle returned by iommu_sva_bind_device()
 *
 * Put reference to a bond between device and address space. The device should
 * not be issuing any more transaction for this PASID. All outstanding page
 * requests for this PASID must have been flushed to the IOMMU.
 */
void iommu_sva_unbind_device(struct iommu_sva *handle)
{
	struct iommu_domain *domain = handle->handle.domain;
	struct iommu_mm_data *iommu_mm = domain->mm->iommu_mm;
	struct device *dev = handle->dev;

	mutex_lock(&iommu_sva_lock);
	if (!refcount_dec_and_test(&handle->users)) {
		mutex_unlock(&iommu_sva_lock);
		return;
	}

	iommu_sva_untrack_mm(domain->mm);
	iommu_detach_device_pasid(domain, dev, iommu_mm->pasid);
	if (--domain->users == 0) {
		list_del(&domain->next);
		iommu_domain_free(domain);
	}
	mutex_unlock(&iommu_sva_lock);
	kfree(handle);
}
EXPORT_SYMBOL_GPL(iommu_sva_unbind_device);

u32 iommu_sva_get_pasid(struct iommu_sva *handle)
{
	struct iommu_domain *domain = handle->handle.domain;

	return mm_get_enqcmd_pasid(domain->mm);
}
EXPORT_SYMBOL_GPL(iommu_sva_get_pasid);

void mm_pasid_drop(struct mm_struct *mm)
{
	struct iommu_mm_data *iommu_mm = mm->iommu_mm;

	if (!iommu_mm)
		return;

	iommu_free_global_pasid(iommu_mm->pasid);
	kfree(iommu_mm);
}

/*
 * I/O page fault handler for SVA
 */
static enum iommu_page_response_code
iommu_sva_handle_mm(struct iommu_fault *fault, struct mm_struct *mm)
{
	vm_fault_t ret;
	struct vm_area_struct *vma;
	unsigned int access_flags = 0;
	unsigned int fault_flags = FAULT_FLAG_REMOTE;
	struct iommu_fault_page_request *prm = &fault->prm;
	enum iommu_page_response_code status = IOMMU_PAGE_RESP_INVALID;

	if (!(prm->flags & IOMMU_FAULT_PAGE_REQUEST_PASID_VALID))
		return status;

	if (!mmget_not_zero(mm))
		return status;

	mmap_read_lock(mm);

	vma = vma_lookup(mm, prm->addr);
	if (!vma)
		/* Unmapped area */
		goto out_put_mm;

	if (prm->perm & IOMMU_FAULT_PERM_READ)
		access_flags |= VM_READ;

	if (prm->perm & IOMMU_FAULT_PERM_WRITE) {
		access_flags |= VM_WRITE;
		fault_flags |= FAULT_FLAG_WRITE;
	}

	if (prm->perm & IOMMU_FAULT_PERM_EXEC) {
		access_flags |= VM_EXEC;
		fault_flags |= FAULT_FLAG_INSTRUCTION;
	}

	if (!(prm->perm & IOMMU_FAULT_PERM_PRIV))
		fault_flags |= FAULT_FLAG_USER;

	if (access_flags & ~vma->vm_flags)
		/* Access fault */
		goto out_put_mm;

	ret = handle_mm_fault(vma, prm->addr, fault_flags, NULL);
	status = ret & VM_FAULT_ERROR ? IOMMU_PAGE_RESP_INVALID :
		IOMMU_PAGE_RESP_SUCCESS;

out_put_mm:
	mmap_read_unlock(mm);
	mmput(mm);

	return status;
}

static void iommu_sva_handle_iopf(struct work_struct *work)
{
	struct iopf_fault *iopf;
	struct iopf_group *group;
	enum iommu_page_response_code status = IOMMU_PAGE_RESP_SUCCESS;

	group = container_of(work, struct iopf_group, work);
	list_for_each_entry(iopf, &group->faults, list) {
		/*
		 * For the moment, errors are sticky: don't handle subsequent
		 * faults in the group if there is an error.
		 */
		if (status != IOMMU_PAGE_RESP_SUCCESS)
			break;

		status = iommu_sva_handle_mm(&iopf->fault,
					     group->attach_handle->domain->mm);
	}

	iopf_group_response(group, status);
	iopf_free_group(group);
}

static int iommu_sva_iopf_handler(struct iopf_group *group)
{
	struct iommu_fault_param *fault_param = group->fault_param;

	INIT_WORK(&group->work, iommu_sva_handle_iopf);
	if (!queue_work(fault_param->queue->wq, &group->work))
		return -EBUSY;

	return 0;
}

static struct iommu_domain *iommu_sva_domain_alloc(struct device *dev,
						   struct mm_struct *mm)
{
	const struct iommu_ops *ops = dev_iommu_ops(dev);
	struct iommu_domain *domain;

	if (!ops->domain_alloc_sva)
		return ERR_PTR(-EOPNOTSUPP);

	domain = ops->domain_alloc_sva(dev, mm);
	if (IS_ERR(domain))
		return domain;

	domain->type = IOMMU_DOMAIN_SVA;
	domain->cookie_type = IOMMU_COOKIE_SVA;
	mmgrab(mm);
	domain->mm = mm;
	domain->owner = ops;
	domain->iopf_handler = iommu_sva_iopf_handler;

	return domain;
}

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
 * Called when SVA is bound for this mm.  If the mm is already tracked,
 * increments the refcount.  Otherwise allocates a new tracking entry.
 *
 * Returns 0 on success, -ENOMEM on allocation failure.
 */
static int iommu_sva_track_mm(struct mm_struct *mm)
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
	if (!smm)
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

/**
 * iommu_sva_untrack_mm - Stop tracking an mm for kernel PT change notification
 * @mm: the mm_struct to untrack
 *
 * Called when SVA is unbound for this mm.  Decrements the refcount and
 * removes the tracking entry when it reaches zero.
 */
static void iommu_sva_untrack_mm(struct mm_struct *mm)
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

/**
 * iommu_sva_invalidate_kva_range - Flush IOMMU caches before kernel PT free
 * @start: Start of kernel virtual address range
 * @end: End of kernel virtual address range
 *
 * Called from x86 mm code before freeing kernel page table pages.
 * Iterates all tracked SVA-bound mm_structs and calls
 * mmu_notifier_arch_invalidate_secondary_tlbs() for each, triggering
 * IOTLB flushes via the drivers' invalidate_range callbacks.
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
			mmu_notifier_arch_invalidate_secondary_tlbs(smm->mm, start, end);
			mmput_async(smm->mm);
		}
	}
	rcu_read_unlock();
}
