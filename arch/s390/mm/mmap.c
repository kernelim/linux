/*
 *  linux/arch/s390/mm/mmap.c
 *
 *  flexible mmap layout support
 *
 * Copyright 2003-2004 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *
 *
 * Started by Ingo Molnar <mingo@elte.hu>
 */

#include <linux/personality.h>
#include <linux/mm.h>
#include <linux/mman.h>
#include <linux/module.h>
#include <linux/random.h>
#include <asm/pgalloc.h>
#include <asm/compat.h>

unsigned long mmap_rnd_mask;
unsigned long mmap_align_mask;

static unsigned long stack_maxrandom_size(void)
{
	if (!(current->flags & PF_RANDOMIZE))
		return 0;
	if (current->personality & ADDR_NO_RANDOMIZE)
		return 0;
	return STACK_RND_MASK << PAGE_SHIFT;
}

/*
 * Top of mmap area (just below the process stack).
 *
 * Leave at least a ~32 MB hole.
 */
#define MIN_GAP (32*1024*1024)
#define MAX_GAP (STACK_TOP/6*5)

static inline int mmap_is_legacy(void)
{
	if (current->personality & ADDR_COMPAT_LAYOUT)
		return 1;
	if (current->signal->rlim[RLIMIT_STACK].rlim_cur == RLIM_INFINITY)
		return 1;
	return sysctl_legacy_va_layout;
}

unsigned long arch_mmap_rnd(void)
{
	if (is_32bit_task())
		return (get_random_int() & 0x7ff) << PAGE_SHIFT;
	else
		return (get_random_int() & mmap_rnd_mask) << PAGE_SHIFT;
}

static unsigned long mmap_base_legacy(unsigned long rnd)
{
	return TASK_UNMAPPED_BASE + rnd;
}

static inline unsigned long mmap_base(unsigned long rnd)
{
	unsigned long gap = current->signal->rlim[RLIMIT_STACK].rlim_cur;

	if (gap < MIN_GAP)
		gap = MIN_GAP;
	else if (gap > MAX_GAP)
		gap = MAX_GAP;
	gap &= PAGE_MASK;
	return STACK_TOP - stack_maxrandom_size() - rnd - gap;
}

static inline unsigned long COLOUR_ALIGN(unsigned long addr,
                                         unsigned long pgoff)
{
	unsigned long base = (addr + mmap_align_mask) & ~mmap_align_mask;
	unsigned long off = (pgoff << PAGE_SHIFT) & mmap_align_mask;

	return base + off;
}

static inline unsigned long COLOUR_ALIGN_DOWN(unsigned long addr,
                                              unsigned long pgoff)
{
	unsigned long base = addr & ~mmap_align_mask;
	unsigned long off = (pgoff << PAGE_SHIFT) & mmap_align_mask;

	if (base + off <= addr)
		return base + off;
	return base - off;
}

unsigned long
arch_get_unmapped_area(struct file *filp, unsigned long addr,
		unsigned long len, unsigned long pgoff, unsigned long flags)
{
	struct mm_struct *mm = current->mm;
	struct vm_area_struct *vma;
	unsigned long start_addr;
	int do_color_align;

	if (flags & MAP_FIXED)
		return addr;

	if (len > TASK_SIZE)
		return -ENOMEM;

	if (addr) {
		addr = PAGE_ALIGN(addr);
		vma = find_vma(mm, addr);
		if (TASK_SIZE - len >= addr &&
		    (!vma || addr + len <= vm_start_gap(vma))) {
			return addr;
		}
	}

	do_color_align = 0;
	if (filp || (flags & MAP_SHARED))
		do_color_align = !is_32bit_task();

	if (len > mm->cached_hole_size) {
		addr = mm->free_area_cache;
	} else {
		mm->cached_hole_size = 0;
		addr = TASK_UNMAPPED_BASE;
        }
	start_addr = addr;

full_search:
	if (do_color_align)
		addr = COLOUR_ALIGN(addr, pgoff);
	else
		addr = PAGE_ALIGN(addr);

	for (vma = find_vma(mm, addr); ; vma = vma->vm_next) {
		/* At this point:  (!vma || addr < vma->vm_end). */
		if (TASK_SIZE - len < addr) {
			/*
			 * Start a new search - just in case we missed
			 * some holes.
			 */
			if (start_addr != TASK_UNMAPPED_BASE) {
				mm->cached_hole_size = 0;
				addr = TASK_UNMAPPED_BASE;
				start_addr = addr;
				goto full_search;
			}
			return -ENOMEM;
		}
		if (!vma || addr + len <= vma->vm_start) {
			/*
			 * Remember the place where we stopped the search:
			 */
			mm->free_area_cache = addr + len;
			return addr;
		}
		if (addr + mm->cached_hole_size < vma->vm_start)
			mm->cached_hole_size = vma->vm_start - addr;
		addr = vma->vm_end;
		if (do_color_align)
			addr = COLOUR_ALIGN(addr, pgoff);
        }
}

unsigned long
arch_get_unmapped_area_topdown(struct file *filp, const unsigned long addr0,
			  const unsigned long len, const unsigned long pgoff,
			  const unsigned long flags)
{
	struct vm_area_struct *vma;
	struct mm_struct *mm = current->mm;
	unsigned long addr = addr0;
	int do_color_align;


	if (flags & MAP_FIXED)
		return addr;

	/* requested length too big for entire address space */
	if (len > TASK_SIZE)
		return -ENOMEM;

	/* requesting a specific address */
	if (addr) {
		addr = PAGE_ALIGN(addr);
		vma = find_vma(mm, addr);
		if (TASK_SIZE - len >= addr &&
		    (!vma || addr + len <= vma->vm_start))
			return addr;
	}

	do_color_align = 0;
	if (filp || (flags & MAP_SHARED))
		do_color_align = !is_32bit_task();

	/* check if free_area_cache is useful for us */
	if (len <= mm->cached_hole_size) {
		mm->cached_hole_size = 0;
		mm->free_area_cache = mm->mmap_base;
	}

	/* either no address requested or can't fit in requested address hole */
	addr = mm->free_area_cache;
	if (do_color_align)
		addr = COLOUR_ALIGN_DOWN(addr - len, pgoff) + len;

	/* make sure it can fit in the remaining address space */
	if (addr > len) {
		vma = find_vma(mm, addr - len);
		if (!vma || addr <= vma->vm_start)
			/* remember the address as a hint for next time */
			return (mm->free_area_cache = addr - len);
	}

	if (mm->mmap_base < len)
		goto bottomup;

	addr = mm->mmap_base - len;
	if (do_color_align)
		addr = COLOUR_ALIGN_DOWN(addr, pgoff);

	do {
		/*
		 * Lookup failure means no vma is above this address,
		 * else if new region fits below vma->vm_start,
		 * return with success:
		 */
		vma = find_vma(mm, addr);
		if (!vma || addr + len <= vma->vm_start)
			/* remember the address as a hint for next time */
			return (mm->free_area_cache = addr);

                /* remember the largest hole we saw so far */
		if (addr + mm->cached_hole_size < vma->vm_start)
			mm->cached_hole_size = vma->vm_start - addr;

                /* try just below the current vma->vm_start */
		addr = vma->vm_start - len;
		if (do_color_align)
			addr = COLOUR_ALIGN_DOWN(addr, pgoff);
	} while (len < vma->vm_start);

bottomup:
	/*
	 * A failed mmap() very likely causes application failure,
	 * so fall back to the bottom-up function here. This scenario
	 * can happen with large stack limits and large mmap()
	 * allocations.
	 */
	mm->cached_hole_size = ~0UL;
	mm->free_area_cache = TASK_UNMAPPED_BASE;
	addr = arch_get_unmapped_area(filp, addr0, len, pgoff, flags);
	/*
	 * Restore the topdown base:
	 */
	mm->free_area_cache = mm->mmap_base;
	mm->cached_hole_size = ~0UL;

	return addr;
}

#ifndef CONFIG_64BIT

/*
 * This function, called very early during the creation of a new
 * process VM image, sets up which VM layout function to use:
 */
void arch_pick_mmap_layout(struct mm_struct *mm)
{
	unsigned long random_factor = 0UL;

	if (current->flags & PF_RANDOMIZE)
		random_factor = arch_mmap_rnd();

	/*
	 * Fall back to the standard layout if the personality
	 * bit is set, or if the expected stack growth is unlimited:
	 */
	if (mmap_is_legacy()) {
		mm->mmap_base = mmap_base_legacy(random_factor);
		mm->get_unmapped_area = arch_get_unmapped_area;
		mm->unmap_area = arch_unmap_area;
	} else {
		mm->mmap_base = mmap_base(random_factor);
		mm->get_unmapped_area = arch_get_unmapped_area_topdown;
		mm->unmap_area = arch_unmap_area_topdown;
	}
}
EXPORT_SYMBOL_GPL(arch_pick_mmap_layout);

#else

int s390_mmap_check(unsigned long addr, unsigned long len, unsigned long flags)
{
	if (is_compat_task() || (TASK_SIZE >= (1UL << 53)))
		return 0;
	if (!(flags & MAP_FIXED))
		addr = 0;
	if ((addr + len) >= TASK_SIZE)
		return crst_table_upgrade(current->mm);
	return 0;
}

static unsigned long
s390_get_unmapped_area(struct file *filp, unsigned long addr,
		unsigned long len, unsigned long pgoff, unsigned long flags)
{
	struct mm_struct *mm = current->mm;
	unsigned long area;
	int rc;

	area = arch_get_unmapped_area(filp, addr, len, pgoff, flags);
	if (!(area & ~PAGE_MASK))
		return area;
	if (area == -ENOMEM && !is_compat_task() && TASK_SIZE < (1UL << 53)) {
		/* Upgrade the page table to 4 levels and retry. */
		rc = crst_table_upgrade(mm);
		if (rc)
			return (unsigned long) rc;
		area = arch_get_unmapped_area(filp, addr, len, pgoff, flags);
	}
	return area;
}

static unsigned long
s390_get_unmapped_area_topdown(struct file *filp, const unsigned long addr,
			  const unsigned long len, const unsigned long pgoff,
			  const unsigned long flags)
{
	struct mm_struct *mm = current->mm;
	unsigned long area;
	int rc;

	area = arch_get_unmapped_area_topdown(filp, addr, len, pgoff, flags);
	if (!(area & ~PAGE_MASK))
		return area;
	if (area == -ENOMEM && !is_compat_task() && TASK_SIZE < (1UL << 53)) {
		/* Upgrade the page table to 4 levels and retry. */
		rc = crst_table_upgrade(mm);
		if (rc)
			return (unsigned long) rc;
		area = arch_get_unmapped_area_topdown(filp, addr, len,
						      pgoff, flags);
	}
	return area;
}
/*
 * This function, called very early during the creation of a new
 * process VM image, sets up which VM layout function to use:
 */
void arch_pick_mmap_layout(struct mm_struct *mm)
{
	unsigned long random_factor = 0UL;

	if (current->flags & PF_RANDOMIZE)
		random_factor = arch_mmap_rnd();

	/*
	 * Fall back to the standard layout if the personality
	 * bit is set, or if the expected stack growth is unlimited:
	 */
	if (mmap_is_legacy()) {
		mm->mmap_base = mmap_base_legacy(random_factor);
		mm->get_unmapped_area = s390_get_unmapped_area;
		mm->unmap_area = arch_unmap_area;
	} else {
		mm->mmap_base = mmap_base(random_factor);
		mm->get_unmapped_area = s390_get_unmapped_area_topdown;
		mm->unmap_area = arch_unmap_area_topdown;
	}
}
EXPORT_SYMBOL_GPL(arch_pick_mmap_layout);

static int __init setup_mmap_rnd(void)
{
	struct cpuid cpu_id;

	get_cpu_id(&cpu_id);
	switch (cpu_id.machine) {
	case 0x9672:
	case 0x2064:
	case 0x2066:
	case 0x2084:
	case 0x2086:
	case 0x2094:
	case 0x2096:
	case 0x2097:
	case 0x2098:
	case 0x2817:
	case 0x2818:
	case 0x2827:
	case 0x2828:
		mmap_rnd_mask = 0x7ffUL;
		mmap_align_mask = 0xfffUL;
		break;
	case 0x2964:	/* z13 */
	default:
		mmap_rnd_mask = 0x3ff80UL;
		mmap_align_mask = 0x7ffffUL;
		break;
	}
	return 0;
}
early_initcall(setup_mmap_rnd);

#endif
