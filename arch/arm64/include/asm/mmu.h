/*
 * Copyright (C) 2012 ARM Ltd.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
#ifndef __ASM_MMU_H
#define __ASM_MMU_H

#include <asm/cputype.h>

#define MMCF_AARCH32	0x1	/* mm context flag for AArch32 executables */
#define USER_ASID_BIT	48
#define USER_ASID_FLAG	(UL(1) << USER_ASID_BIT)
#define TTBR_ASID_MASK	(UL(0xffff) << 48)

#define BP_HARDEN_EL2_SLOTS 4
#define __BP_HARDEN_HYP_VECS_SZ (BP_HARDEN_EL2_SLOTS * SZ_2K)

#ifndef __ASSEMBLY__

typedef struct {
	atomic64_t	id;
#ifdef CONFIG_COMPAT
	void		*sigpage;
#endif
	void		*vdso;
	unsigned long	flags;
	atomic_t	nr_active_mm;
} mm_context_t;

/*
 * We use atomic64_read() here because the ASID for an 'mm_struct' can
 * be reallocated when scheduling one of its threads following a
 * rollover event (see new_context() and flush_context()). In this case,
 * a concurrent TLBI (e.g. via try_to_unmap_one() and ptep_clear_flush())
 * may use a stale ASID. This is fine in principle as the new ASID is
 * guaranteed to be clean in the TLB, but the TLBI routines have to take
 * care to handle the following race:
 *
 *    CPU 0                    CPU 1                          CPU 2
 *
 *    // ptep_clear_flush(mm)
 *    xchg_relaxed(pte, 0)
 *    DSB ISHST
 *    old = ASID(mm)
 *         |                                                  <rollover>
 *         |                   new = new_context(mm)
 *         \-----------------> atomic_set(mm->context.id, new)
 *                             cpu_switch_mm(mm)
 *                             // Hardware walk of pte using new ASID
 *    TLBI(old)
 *
 * In this scenario, the barrier on CPU 0 and the dependency on CPU 1
 * ensure that the page-table walker on CPU 1 *must* see the invalid PTE
 * written by CPU 0.
 */
#define __ASID(asid)	((asid) & 0xffff)
#define ASID(mm)	__ASID(atomic64_read(&(mm)->context.id) & 0xffff)

static __always_inline bool arm64_kernel_unmapped_at_el0(void)
{
	return cpus_have_const_cap(ARM64_UNMAP_KERNEL_AT_EL0);
}

typedef void (*bp_hardening_cb_t)(void);

struct bp_hardening_data {
	int			hyp_vectors_slot;
	bp_hardening_cb_t	fn;

	/*
	 * template_start is only used by the BHB mitigation to identify the
	 * hyp_vectors_slot sequence.
	 */
	const char *template_start;
};

DECLARE_PER_CPU_READ_MOSTLY(struct bp_hardening_data, bp_hardening_data);

static inline struct bp_hardening_data *arm64_get_bp_hardening_data(void)
{
	return this_cpu_ptr(&bp_hardening_data);
}

static inline void arm64_apply_bp_hardening(void)
{
	struct bp_hardening_data *d;

	if (!cpus_have_const_cap(ARM64_HARDEN_BRANCH_PREDICTOR))
		return;

	d = arm64_get_bp_hardening_data();
	if (d->fn)
		d->fn();
}

extern void arm64_memblock_init(void);
extern void paging_init(void);
extern void bootmem_init(void);
extern void __iomem *early_io_map(phys_addr_t phys, unsigned long virt);
extern void init_mem_pgprot(void);
extern void create_pgd_mapping(struct mm_struct *mm, phys_addr_t phys,
			       unsigned long virt, phys_addr_t size,
			       pgprot_t prot, bool page_mappings_only);
extern void *fixmap_remap_fdt(phys_addr_t dt_phys, int *size, pgprot_t prot);
extern void mark_linear_text_alias_ro(void);
extern bool kaslr_requires_kpti(void);

#define INIT_MM_CONTEXT(name)	\
	.pgd = init_pg_dir,

#endif	/* !__ASSEMBLY__ */
#endif
