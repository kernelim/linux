#ifndef _ASM_X86_PGTABLE_3LEVEL_H
#define _ASM_X86_PGTABLE_3LEVEL_H

/*
 * Intel Physical Address Extension (PAE) Mode - three-level page
 * tables on PPro+ CPUs.
 *
 * Copyright (C) 1999 Ingo Molnar <mingo@redhat.com>
 */

#define pte_ERROR(e)							\
	printk("%s:%d: bad pte %p(%08lx%08lx).\n",			\
	       __FILE__, __LINE__, &(e), (e).pte_high, (e).pte_low)
#define pmd_ERROR(e)							\
	printk("%s:%d: bad pmd %p(%016Lx).\n",				\
	       __FILE__, __LINE__, &(e), pmd_val(e))
#define pgd_ERROR(e)							\
	printk("%s:%d: bad pgd %p(%016Lx).\n",				\
	       __FILE__, __LINE__, &(e), pgd_val(e))

/* Rules for using set_pte: the pte being assigned *must* be
 * either not present or in a state where the hardware will
 * not attempt to update the pte.  In places where this is
 * not possible, use pte_get_and_clear to obtain the old pte
 * value and then use set_pte to update it.  -ben
 */
static inline void native_set_pte(pte_t *ptep, pte_t pte)
{
	mm_track_pte(ptep);
	ptep->pte_high = pte.pte_high;
	smp_wmb();
	ptep->pte_low = pte.pte_low;
}

#define  __HAVE_ARCH_READ_PMD_ATOMIC
/*
 * pte_offset_map_lock on 32bit PAE kernels was reading the pmd_t with
 * a "*pmdp" dereference done by gcc. Problem is, in certain places
 * where pte_offset_map_lock is called, concurrent page faults are
 * allowed, if the mmap_sem is hold for reading. An example is mincore
 * vs page faults vs MADV_DONTNEED. On the page fault side
 * pmd_populate rightfully does a set_64bit, but if we're reading the
 * pmd_t with a "*pmdp" on the mincore side, a SMP race can happen
 * because gcc will not read the 64bit of the pmd atomically. To fix
 * this all places running pmd_offset_map_lock() while holding the
 * mmap_sem in read mode, shall read the pmdp pointer using this
 * function to know if the pmd is null nor not, and in turn to know if
 * they can run pmd_offset_map_lock or pmd_trans_huge or other pmd
 * operations.
 *
 * Without THP if the mmap_sem is hold for reading, the
 * pmd can only transition from null to not null while read_pmd_atomic runs.
 * So there's no need of literally reading it atomically.
 *
 * With THP if the mmap_sem is hold for reading, the pmd can become
 * THP or null or point to a pte (and in turn become "stable") at any
 * time under read_pmd_atomic, so it's mandatory to read it atomically
 * with cmpxchg8b.
 */
#ifndef CONFIG_TRANSPARENT_HUGEPAGE
static inline pmd_t read_pmd_atomic(pmd_t *pmdp)
{
	pmdval_t ret;
	u32 *tmp = (u32 *)pmdp;

	ret = (pmdval_t) (*tmp);
	if (ret) {
		/*
		 * If the low part is null, we must not read the high part
		 * or we can end up with a partial pmd.
		 */
		smp_rmb();
		ret |= ((pmdval_t)*(tmp + 1)) << 32;
	}

	return (pmd_t) { ret };
}
#else /* CONFIG_TRANSPARENT_HUGEPAGE */
static inline pmd_t read_pmd_atomic(pmd_t *pmdp)
{
	pmdval_t val = (pmdval_t)atomic64_read((atomic64_t *)pmdp);
	return (pmd_t) { val };
}
#endif /* CONFIG_TRANSPARENT_HUGEPAGE */

static inline void native_set_pte_atomic(pte_t *ptep, pte_t pte)
{
	mm_track_pte(ptep);
	set_64bit((unsigned long long *)(ptep), native_pte_val(pte));
}

static inline void native_set_pmd(pmd_t *pmdp, pmd_t pmd)
{
	mm_track_pmd(pmdp);
	set_64bit((unsigned long long *)(pmdp), native_pmd_val(pmd));
}

/*
 * PHYSICAL_PAGE_MASK is casted to 32 bits, so we can't use it here.
 */
#define PGD_PAE_PHYS_MASK	(__PHYSICAL_MASK & PAGE_MASK)

/*
 * PAE allows Base Address, P, PWT, PCD and AVL bits to be set in PGD entries.
 * Bits 9-11 are ignored. All other bits are Reserved (must be zero).
 */
#define PGD_ALLOWED_BITS	(PGD_PAE_PHYS_MASK | _PAGE_PRESENT | \
				 _PAGE_PWT | _PAGE_PCD | \
				 _PAGE_UNUSED1 | _PAGE_IOMAP | _PAGE_HIDDEN)

static inline void native_set_pud(pud_t *pudp, pud_t pud)
{
	mm_track_pud(pudp);
#ifdef CONFIG_PAGE_TABLE_ISOLATION
	pud.pgd.pgd &= PGD_ALLOWED_BITS;
	pud.pgd = pti_set_user_pgd((pgd_t *)pudp, pud.pgd);
#endif
	set_64bit((unsigned long long *)(pudp), native_pud_val(pud));
}

#ifdef CONFIG_PAGE_TABLE_ISOLATION
/*
 * The NX bit isn't allowed in the PDPTE (PGD) entries in Physical Address
 * Extension (PAE) mode. As a result, PGD entry poisoning for user PGD
 * entries won't work.
 */

static inline void kaiser_poison_pgd(pgd_t *pgd)
{
}

static inline void kaiser_unpoison_pgd(pgd_t *pgd)
{
}

static inline void kaiser_poison_pgd_atomic(pgd_t *pgd)
{
}

static inline void kaiser_unpoison_pgd_atomic(pgd_t *pgd)
{
}
#endif

/*
 * For PTEs and PDEs, we must clear the P-bit first when clearing a page table
 * entry, so clear the bottom half first and enforce ordering with a compiler
 * barrier.
 */
static inline void native_pte_clear(struct mm_struct *mm, unsigned long addr,
				    pte_t *ptep)
{
	mm_track_pte(ptep);
	ptep->pte_low = 0;
	smp_wmb();
	ptep->pte_high = 0;
}

static inline void native_pmd_clear(pmd_t *pmd)
{
	u32 *tmp = (u32 *)pmd;

	mm_track_pmd(pmd);

	*tmp = 0;
	smp_wmb();
	*(tmp + 1) = 0;
}

static inline void pud_clear(pud_t *pudp)
{

	mm_track_pud(pudp);
	set_pud(pudp, __pud(0));

#ifdef CONFIG_PAGE_TABLE_ISOLATION
	pti_set_user_pgd((pgd_t *)pudp, __pgd(0));
#endif

	/*
	 * According to Intel App note "TLBs, Paging-Structure Caches,
	 * and Their Invalidation", April 2007, document 317080-001,
	 * section 8.1: in PAE mode we explicitly have to flush the
	 * TLB via cr3 if the top-level pgd is changed...
	 *
	 * Currently all places where pud_clear() is called either have
	 * flush_tlb_mm() followed or don't need TLB flush (x86_64 code or
	 * pud_clear_bad()), so we don't need TLB flush here.
 	 */
}

#ifdef CONFIG_SMP
static inline pte_t native_ptep_get_and_clear(pte_t *ptep)
{
	pte_t res;

	mm_track_pte(ptep);

	/* xchg acts as a barrier before the setting of the high bits */
	res.pte_low = xchg(&ptep->pte_low, 0);
	res.pte_high = ptep->pte_high;
	ptep->pte_high = 0;

	return res;
}
#else
#define native_ptep_get_and_clear(xp) native_local_ptep_get_and_clear(xp)
#endif

/*
 * Bits 0, 6 and 7 are taken in the low part of the pte.
 * The 32 bits of offset is split into both the lower and upper 32 bits
 * of the pte as follows:
 *
 * Bits  0-08: _PAGE_FILE
 * Bits  9-24: low 16 bits of the offset
 * Bits 25-31: 1s
 * --------------
 * Bits 32-47: 1s
 * Bits 48-63: high 16 bits of the offset
 *
 * So unless the system has more than (MAX-PA - 32M) of memory, the offset
 * entry won't match any of the physical memory addresses.
 */
#define _PGOFF_ENTRY_SHIFT	9
#define _PGOFF_HI16_MASK	0xffff0000
#define _PGOFF_LO16_MASK	0x0000ffff

#define pte_to_pgoff(pte)			\
	(((pte).pte_high & _PGOFF_HI16_MASK) |	\
	(((pte).pte_low >>_PGOFF_ENTRY_SHIFT) & _PGOFF_LO16_MASK))
#define pgoff_to_pte(off) ((pte_t) { {		\
	.pte_low = _PAGE_FILE |			\
	(((off) | _PGOFF_HI16_MASK) << _PGOFF_ENTRY_SHIFT),	\
	.pte_high = (off) | _PGOFF_LO16_MASK } })
#define PTE_FILE_MAX_BITS       32

/*
 * Encode and de-code a swap entry
 *
 * With a maximum supported physical address bit size of 46, there are 18
 * high order bits available. So we can split the 32-bit swap entry into 2
 * 16-bit halves and put them into the high and low 32-bit words of the PTE
 * as follows:
 *
 *  bits  0-08: 0s
 *  bits  9-24: low 16 bits of swap entry
 *  bits 25-31: 1s
 *  --------------
 *  bits 32-47: 1s
 *  bits 48-63: high 16 bits of swap entry
 *
 * So unless the system has more than (MAX-PA - 32M) of memory, the swap
 * entry won't match any of the physical memory addresses.
 */
#define MAX_SWAPFILES_CHECK() BUILD_BUG_ON(MAX_SWAPFILES_SHIFT > 5)
#define __swp_type(x)			(((x).val) & 0x1f)
#define __swp_offset(x)			((x).val >> 5)
#define __swp_entry(type, offset)	((swp_entry_t){(type) | (offset) << 5})

#define _PTE_SWAP_ENTRY_SHIFT		9
#define _SWAP_HI16_MASK 		0xffff0000
#define _SWAP_LO16_MASK 		0x0000ffff
#define __pte_to_swp_entry(pte) 	((swp_entry_t) { \
	 ((pte).pte_high & _SWAP_HI16_MASK) | \
	(((pte).pte_low >> _PTE_SWAP_ENTRY_SHIFT) & _SWAP_LO16_MASK) })
#define __swp_entry_to_pte(x)		((pte_t) { { \
	.pte_high =  (x).val | _SWAP_LO16_MASK, \
	.pte_low  = ((x).val | _SWAP_HI16_MASK) << _PTE_SWAP_ENTRY_SHIFT } })

#include <asm/pgtable-invert.h>

#endif /* _ASM_X86_PGTABLE_3LEVEL_H */
