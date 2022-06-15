#include <linux/mm.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/export.h>
#include <linux/err.h>
#include <linux/sched.h>
#include <linux/security.h>
#include <linux/swap.h>
#include <linux/swapops.h>
#include <linux/mman.h>
#include <linux/hugetlb.h>
#include <linux/vmalloc.h>
#include <linux/userfaultfd_k.h>

#include <asm/sections.h>
#include <asm/uaccess.h>

#include "internal.h"

#define CREATE_TRACE_POINTS
#include <trace/events/kmem.h>

static inline int is_kernel_rodata(unsigned long addr)
{
	return addr >= (unsigned long)__start_rodata &&
		addr < (unsigned long)__end_rodata;
}

/**
 * kfree_const - conditionally free memory
 * @x: pointer to the memory
 *
 * Function calls kfree only if @x is not in .rodata section.
 */
void kfree_const(const void *x)
{
	if (!is_kernel_rodata((unsigned long)x))
		kfree(x);
}
EXPORT_SYMBOL(kfree_const);

/**
 * kstrdup - allocate space for and copy an existing string
 * @s: the string to duplicate
 * @gfp: the GFP mask used in the kmalloc() call when allocating memory
 */
char *kstrdup(const char *s, gfp_t gfp)
{
	size_t len;
	char *buf;

	if (!s)
		return NULL;

	len = strlen(s) + 1;
	buf = kmalloc_track_caller(len, gfp);
	if (buf)
		memcpy(buf, s, len);
	return buf;
}
EXPORT_SYMBOL(kstrdup);

/**
 * kstrdup_const - conditionally duplicate an existing const string
 * @s: the string to duplicate
 * @gfp: the GFP mask used in the kmalloc() call when allocating memory
 *
 * Function returns source string if it is in .rodata section otherwise it
 * fallbacks to kstrdup.
 * Strings allocated by kstrdup_const should be freed by kfree_const.
 */
const char *kstrdup_const(const char *s, gfp_t gfp)
{
	if (is_kernel_rodata((unsigned long)s))
		return s;

	return kstrdup(s, gfp);
}
EXPORT_SYMBOL(kstrdup_const);

/**
 * kstrndup - allocate space for and copy an existing string
 * @s: the string to duplicate
 * @max: read at most @max chars from @s
 * @gfp: the GFP mask used in the kmalloc() call when allocating memory
 */
char *kstrndup(const char *s, size_t max, gfp_t gfp)
{
	size_t len;
	char *buf;

	if (!s)
		return NULL;

	len = strnlen(s, max);
	buf = kmalloc_track_caller(len+1, gfp);
	if (buf) {
		memcpy(buf, s, len);
		buf[len] = '\0';
	}
	return buf;
}
EXPORT_SYMBOL(kstrndup);

/**
 * kmemdup - duplicate region of memory
 *
 * @src: memory region to duplicate
 * @len: memory region length
 * @gfp: GFP mask to use
 */
void *kmemdup(const void *src, size_t len, gfp_t gfp)
{
	void *p;

	p = kmalloc_track_caller(len, gfp);
	if (p)
		memcpy(p, src, len);
	return p;
}
EXPORT_SYMBOL(kmemdup);

/**
 * memdup_user - duplicate memory region from user space
 *
 * @src: source address in user space
 * @len: number of bytes to copy
 *
 * Returns an ERR_PTR() on failure.  Result is physically
 * contiguous, to be freed by kfree().
 */
void *memdup_user(const void __user *src, size_t len)
{
	void *p;

	/*
	 * Always use GFP_KERNEL, since copy_from_user() can sleep and
	 * cause pagefault, which makes it pointless to use GFP_NOFS
	 * or GFP_ATOMIC.
	 */
	p = kmalloc_track_caller(len, GFP_KERNEL);
	if (!p)
		return ERR_PTR(-ENOMEM);

	if (copy_from_user(p, src, len)) {
		kfree(p);
		return ERR_PTR(-EFAULT);
	}

	return p;
}
EXPORT_SYMBOL(memdup_user);

static __always_inline void *__do_krealloc(const void *p, size_t new_size,
					   gfp_t flags)
{
	void *ret;
	size_t ks = 0;

	if (p)
		ks = ksize(p);

	if (ks >= new_size)
		return (void *)p;

	ret = kmalloc_track_caller(new_size, flags);
	if (ret && p)
		memcpy(ret, p, ks);

	return ret;
}

/**
 * __krealloc - like krealloc() but don't free @p.
 * @p: object to reallocate memory for.
 * @new_size: how many bytes of memory are required.
 * @flags: the type of memory to allocate.
 *
 * This function is like krealloc() except it never frees the originally
 * allocated buffer. Use this if you don't want to free the buffer immediately
 * like, for example, with RCU.
 */
void *__krealloc(const void *p, size_t new_size, gfp_t flags)
{
	if (unlikely(!new_size))
		return ZERO_SIZE_PTR;

	return __do_krealloc(p, new_size, flags);

}
EXPORT_SYMBOL(__krealloc);

/**
 * krealloc - reallocate memory. The contents will remain unchanged.
 * @p: object to reallocate memory for.
 * @new_size: how many bytes of memory are required.
 * @flags: the type of memory to allocate.
 *
 * The contents of the object pointed to are preserved up to the
 * lesser of the new and old sizes.  If @p is %NULL, krealloc()
 * behaves exactly like kmalloc().  If @new_size is 0 and @p is not a
 * %NULL pointer, the object pointed to is freed.
 */
void *krealloc(const void *p, size_t new_size, gfp_t flags)
{
	void *ret;

	if (unlikely(!new_size)) {
		kfree(p);
		return ZERO_SIZE_PTR;
	}

	ret = __do_krealloc(p, new_size, flags);
	if (ret && p != ret)
		kfree(p);

	return ret;
}
EXPORT_SYMBOL(krealloc);

/**
 * kzfree - like kfree but zero memory
 * @p: object to free memory of
 *
 * The memory of the object @p points to is zeroed before freed.
 * If @p is %NULL, kzfree() does nothing.
 *
 * Note: this function zeroes the whole allocated buffer which can be a good
 * deal bigger than the requested buffer size passed to kmalloc(). So be
 * careful when using this function in performance sensitive code.
 */
void kzfree(const void *p)
{
	size_t ks;
	void *mem = (void *)p;

	if (unlikely(ZERO_OR_NULL_PTR(mem)))
		return;
	ks = ksize(mem);
	memset(mem, 0, ks);
	kfree(mem);
}
EXPORT_SYMBOL(kzfree);

/**
 * vmemdup_user - duplicate memory region from user space
 *
 * @src: source address in user space
 * @len: number of bytes to copy
 *
 * Returns an ERR_PTR() on failure.  Result may be not
 * physically contiguous.  Use kvfree() to free.
 */
void *vmemdup_user(const void __user *src, size_t len)
{
	void *p;

	p = kvmalloc(len, GFP_USER);
	if (!p)
		return ERR_PTR(-ENOMEM);

	if (copy_from_user(p, src, len)) {
		kvfree(p);
		return ERR_PTR(-EFAULT);
	}

	return p;
}
EXPORT_SYMBOL(vmemdup_user);

/*
 * strndup_user - duplicate an existing string from user space
 * @s: The string to duplicate
 * @n: Maximum number of bytes to copy, including the trailing NUL.
 */
char *strndup_user(const char __user *s, long n)
{
	char *p;
	long length;

	length = strnlen_user(s, n);

	if (!length)
		return ERR_PTR(-EFAULT);

	if (length > n)
		return ERR_PTR(-EINVAL);

	p = memdup_user(s, length);

	if (IS_ERR(p))
		return p;

	p[length - 1] = '\0';

	return p;
}
EXPORT_SYMBOL(strndup_user);

/**
 * memdup_user_nul - duplicate memory region from user space and NUL-terminate
 *
 * @src: source address in user space
 * @len: number of bytes to copy
 *
 * Returns an ERR_PTR() on failure.
 */
void *memdup_user_nul(const void __user *src, size_t len)
{
	char *p;

	/*
	 * Always use GFP_KERNEL, since copy_from_user() can sleep and
	 * cause pagefault, which makes it pointless to use GFP_NOFS
	 * or GFP_ATOMIC.
	 */
	p = kmalloc_track_caller(len + 1, GFP_KERNEL);
	if (!p)
		return ERR_PTR(-ENOMEM);

	if (copy_from_user(p, src, len)) {
		kfree(p);
		return ERR_PTR(-EFAULT);
	}
	p[len] = '\0';

	return p;
}
EXPORT_SYMBOL(memdup_user_nul);

void __vma_link_list(struct mm_struct *mm, struct vm_area_struct *vma,
		struct vm_area_struct *prev)
{
	struct vm_area_struct *next;

	vma->vm_prev = prev;
	if (prev) {
		next = prev->vm_next;
		prev->vm_next = vma;
	} else {
		next = mm->mmap;
		mm->mmap = vma;
	}
	vma->vm_next = next;
	if (next)
		next->vm_prev = vma;
}

void __vma_unlink_list(struct mm_struct *mm, struct vm_area_struct *vma)
{
	struct vm_area_struct *prev, *next;

	next = vma->vm_next;
	prev = vma->vm_prev;
	if (prev)
		prev->vm_next = next;
	else
		mm->mmap = next;
	if (next)
		next->vm_prev = prev;
}

/* Check if the vma is being used as a stack by this task */
int vma_is_stack_for_task(struct vm_area_struct *vma, struct task_struct *t)
{
	return (vma->vm_start <= KSTK_ESP(t) && vma->vm_end >= KSTK_ESP(t));
}

#if defined(CONFIG_MMU) && !defined(HAVE_ARCH_PICK_MMAP_LAYOUT)
void arch_pick_mmap_layout(struct mm_struct *mm)
{
	mm->mmap_base = TASK_UNMAPPED_BASE;
	mm->get_unmapped_area = arch_get_unmapped_area;
	mm->unmap_area = arch_unmap_area;
}
#endif

/*
 * Like get_user_pages_fast() except its IRQ-safe in that it won't fall
 * back to the regular GUP.
 * If the architecture not support this function, simply return with no
 * page pinned
 */
int __attribute__((weak)) __get_user_pages_fast(unsigned long start,
				 int nr_pages, int write, struct page **pages)
{
	return 0;
}
EXPORT_SYMBOL_GPL(__get_user_pages_fast);

/**
 * get_user_pages_fast() - pin user pages in memory
 * @start:	starting user address
 * @nr_pages:	number of pages from start to pin
 * @write:	whether pages will be written to
 * @pages:	array that receives pointers to the pages pinned.
 *		Should be at least nr_pages long.
 *
 * Returns number of pages pinned. This may be fewer than the number
 * requested. If nr_pages is 0 or negative, returns 0. If no pages
 * were pinned, returns -errno.
 *
 * get_user_pages_fast provides equivalent functionality to get_user_pages,
 * operating on current and current->mm, with force=0 and vma=NULL. However
 * unlike get_user_pages, it must be called without mmap_sem held.
 *
 * get_user_pages_fast may take mmap_sem and page table locks, so no
 * assumptions can be made about lack of locking. get_user_pages_fast is to be
 * implemented in a way that is advantageous (vs get_user_pages()) when the
 * user memory area is already faulted in and present in ptes. However if the
 * pages have to be faulted in, it may turn out to be slightly slower so
 * callers need to carefully consider what to use. On many architectures,
 * get_user_pages_fast simply falls back to get_user_pages.
 */
int __attribute__((weak)) get_user_pages_fast(unsigned long start,
				int nr_pages, int write, struct page **pages)
{
	struct mm_struct *mm = current->mm;
	return get_user_pages_unlocked(current, mm, start, nr_pages,
				       write, 0, pages);
}
EXPORT_SYMBOL_GPL(get_user_pages_fast);

unsigned long vm_mmap_pgoff(struct file *file, unsigned long addr,
	unsigned long len, unsigned long prot,
	unsigned long flag, unsigned long pgoff)
{
	unsigned long ret;
	struct mm_struct *mm = current->mm;
	unsigned long populate;
	LIST_HEAD(uf);

	ret = security_mmap_file(file, prot, flag);
	if (!ret) {
		down_write(&mm->mmap_sem);
		ret = do_mmap_pgoff(file, addr, len, prot, flag, pgoff,
				    &populate, &uf);
		up_write(&mm->mmap_sem);
		userfaultfd_unmap_complete(mm, &uf);
		if (populate)
			mm_populate(ret, populate);
	}
	return ret;
}

unsigned long vm_mmap(struct file *file, unsigned long addr,
	unsigned long len, unsigned long prot,
	unsigned long flag, unsigned long offset)
{
	if (unlikely(offset + PAGE_ALIGN(len) < offset))
		return -EINVAL;
	if (unlikely(offset & ~PAGE_MASK))
		return -EINVAL;

	return vm_mmap_pgoff(file, addr, len, prot, flag, offset >> PAGE_SHIFT);
}
EXPORT_SYMBOL(vm_mmap);

/**
 * kvmalloc_node - attempt to allocate physically contiguous memory, but upon
 * failure, fall back to non-contiguous (vmalloc) allocation.
 * @size: size of the request.
 * @flags: gfp mask for the allocation - must be compatible (superset) with GFP_KERNEL.
 * @node: numa node to allocate from
 *
 * Uses kmalloc to get the memory but if the allocation fails then falls back
 * to the vmalloc allocator. Use kvfree for freeing the memory.
 *
 * Reclaim modifiers - __GFP_NORETRY and __GFP_NOFAIL are not supported. __GFP_REPEAT
 * is supported only for large (>32kB) allocations, and it should be used only if
 * kmalloc is preferable to the vmalloc fallback, due to visible performance drawbacks.
 *
 * Any use of gfp flags outside of GFP_KERNEL should be consulted with mm people.
 */
void *kvmalloc_node(size_t size, gfp_t flags, int node)
{
	gfp_t kmalloc_flags = flags;
	void *ret;

	/*
	 * vmalloc uses GFP_KERNEL for some internal allocations (e.g page tables)
	 * so the given set of flags has to be compatible.
	 */
	WARN_ON_ONCE((flags & GFP_KERNEL) != GFP_KERNEL);

	/*
	 * Make sure that larger requests are not too disruptive - no OOM
	 * killer and no allocation failure warnings as we have a fallback
	 */
	if (size > PAGE_SIZE) {
		kmalloc_flags |= __GFP_NOWARN;

		/*
		 * We have to override __GFP_REPEAT by __GFP_NORETRY for !costly
		 * requests because there is no other way to tell the allocator
		 * that we want to fail rather than retry endlessly.
		 */
		if (!(kmalloc_flags & __GFP_REPEAT) ||
				(size <= PAGE_SIZE << PAGE_ALLOC_COSTLY_ORDER))
			kmalloc_flags |= __GFP_NORETRY;
	}

	ret = kmalloc_node(size, kmalloc_flags, node);

	/*
	 * It doesn't really make sense to fallback to vmalloc for sub page
	 * requests
	 */
	if (ret || size <= PAGE_SIZE)
		return ret;

	return __vmalloc_node_flags(size, node, flags | __GFP_HIGHMEM);
}
EXPORT_SYMBOL(kvmalloc_node);

void kvfree(const void *addr)
{
	if (is_vmalloc_addr(addr))
		vfree(addr);
	else
		kfree(addr);
}
EXPORT_SYMBOL(kvfree);

struct address_space *page_mapping(struct page *page)
{
	struct address_space *mapping = page->mapping;

	VM_BUG_ON(PageSlab(page));
#ifdef CONFIG_SWAP
	if (unlikely(PageSwapCache(page))) {
		swp_entry_t entry;

		entry.val = page_private(page);
		mapping = swap_address_space(entry);
	} else
#endif
	if ((unsigned long)mapping & PAGE_MAPPING_ANON)
		mapping = NULL;
	return mapping;
}

int overcommit_ratio_handler(struct ctl_table *table, int write,
			     void __user *buffer, size_t *lenp,
			     loff_t *ppos)
{
	int ret;

	ret = proc_dointvec(table, write, buffer, lenp, ppos);
	if (ret == 0 && write)
		sysctl_overcommit_kbytes = 0;
	return ret;
}

int overcommit_kbytes_handler(struct ctl_table *table, int write,
			     void __user *buffer, size_t *lenp,
			     loff_t *ppos)
{
	int ret;

	ret = proc_doulongvec_minmax(table, write, buffer, lenp, ppos);
	if (ret == 0 && write)
		sysctl_overcommit_ratio = 0;
	return ret;
}

/*
 * Committed memory limit enforced when OVERCOMMIT_NEVER policy is used
 */
unsigned long vm_commit_limit(void)
{
	unsigned long allowed;

	if (sysctl_overcommit_kbytes)
		allowed = sysctl_overcommit_kbytes >> (PAGE_SHIFT - 10);
	else
		allowed = ((totalram_pages - hugetlb_total_pages())
			   * sysctl_overcommit_ratio / 100);
	allowed += total_swap_pages;

	return allowed;
}

/**
 * get_cmdline() - copy the cmdline value to a buffer.
 * @task:     the task whose cmdline value to copy.
 * @buffer:   the buffer to copy to.
 * @buflen:   the length of the buffer. Larger cmdline values are truncated
 *            to this length.
 * Returns the size of the cmdline field copied. Note that the copy does
 * not guarantee an ending NULL byte.
 */
int get_cmdline(struct task_struct *task, char *buffer, int buflen)
{
	int res = 0;
	unsigned int len;
	struct mm_struct *mm = get_task_mm(task);
	if (!mm)
		goto out;
	if (!mm->arg_end)
		goto out_mm;	/* Shh! No looking before we're done */

	len = mm->arg_end - mm->arg_start;

	if (len > buflen)
		len = buflen;

	res = access_process_vm(task, mm->arg_start, buffer, len, 0);

	/*
	 * If the nul at the end of args has been overwritten, then
	 * assume application is using setproctitle(3).
	 */
	if (res > 0 && buffer[res-1] != '\0' && len < buflen) {
		len = strnlen(buffer, res);
		if (len < res) {
			res = len;
		} else {
			len = mm->env_end - mm->env_start;
			if (len > buflen - res)
				len = buflen - res;
			res += access_process_vm(task, mm->env_start,
						 buffer+res, len, 0);
			res = strnlen(buffer, res);
		}
	}
out_mm:
	mmput(mm);
out:
	return res;
}

/* Tracepoints definitions. */
EXPORT_TRACEPOINT_SYMBOL(kmalloc);
EXPORT_TRACEPOINT_SYMBOL(kmem_cache_alloc);
EXPORT_TRACEPOINT_SYMBOL(kmalloc_node);
EXPORT_TRACEPOINT_SYMBOL(kmem_cache_alloc_node);
EXPORT_TRACEPOINT_SYMBOL(kfree);
EXPORT_TRACEPOINT_SYMBOL(kmem_cache_free);
