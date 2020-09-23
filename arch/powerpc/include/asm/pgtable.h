/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_POWERPC_PGTABLE_H
#define _ASM_POWERPC_PGTABLE_H

#ifndef __ASSEMBLY__
#include <linux/mmdebug.h>
#include <linux/mmzone.h>
#include <asm/processor.h>		/* For TASK_SIZE */
#include <asm/mmu.h>
#include <asm/page.h>
#include <asm/tlbflush.h>

struct mm_struct;

#endif /* !__ASSEMBLY__ */

#ifdef CONFIG_PPC_BOOK3S
#include <asm/book3s/pgtable.h>
#else
#include <asm/nohash/pgtable.h>
#endif /* !CONFIG_PPC_BOOK3S */

#ifndef __ASSEMBLY__

#include <asm/tlbflush.h>

/* Keep these as a macros to avoid include dependency mess */
#define pte_page(x)		pfn_to_page(pte_pfn(x))
#define mk_pte(page, pgprot)	pfn_pte(page_to_pfn(page), (pgprot))

/*
 * ZERO_PAGE is a global shared page that is always zero: used
 * for zero-mapped memory areas etc..
 */
extern unsigned long empty_zero_page[];
#define ZERO_PAGE(vaddr) (virt_to_page(empty_zero_page))

extern pgd_t swapper_pg_dir[];

extern void paging_init(void);

/*
 * kern_addr_valid is intended to indicate whether an address is a valid
 * kernel address.  Most 32-bit archs define it as always true (like this)
 * but most 64-bit archs actually perform a test.  What should we do here?
 */
#define kern_addr_valid(addr)	(1)

#include <asm-generic/pgtable.h>

extern int gup_hugepte(pte_t *ptep, unsigned long sz, unsigned long addr,
		       unsigned long end, int write,
		       struct page **pages, int *nr);
#ifndef CONFIG_TRANSPARENT_HUGEPAGE
#define pmd_large(pmd)		0
#endif

/* can we use this in kvm */
unsigned long vmalloc_to_phys(void *vmalloc_addr);

void pgtable_cache_add(unsigned shift, void (*ctor)(void *));
void pgtable_cache_init(void);

#if defined(CONFIG_STRICT_KERNEL_RWX) || defined(CONFIG_PPC32)
void mark_initmem_nx(void);
#else
static inline void mark_initmem_nx(void) { }
#endif

#ifdef CONFIG_PPC64
#define is_ioremap_addr is_ioremap_addr
static inline bool is_ioremap_addr(const void *x)
{
#ifdef CONFIG_MMU
	unsigned long addr = (unsigned long)x;

	return addr >= IOREMAP_BASE && addr < IOREMAP_END;
#else
	return false;
#endif
}
#endif /* CONFIG_PPC64 */

#endif /* __ASSEMBLY__ */

#endif /* _ASM_POWERPC_PGTABLE_H */
