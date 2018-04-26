#ifndef _ASM_X86_KAISER_H
#define _ASM_X86_KAISER_H
/*
 * Copyright(c) 2017 Intel Corporation. All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of version 2 of the GNU General Public License as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * Based on work published here: https://github.com/IAIK/KAISER
 * Modified by Dave Hansen <dave.hansen@intel.com to actually work.
 */

#define KAISER_SHADOW_PCID_ASID	1

#define KAISER_PCP_ENABLED	(1<<0)
#define KAISER_PCP_PCID		(1<<1)

#ifndef __ASSEMBLY__

#ifdef CONFIG_PAGE_TABLE_ISOLATION
#include <linux/percpu.h>

/**
 *  kaiser_add_mapping - map a kernel range into the user page tables
 *  @addr: the start address of the range
 *  @size: the size of the range
 *  @flags: The mapping flags of the pages
 *
 *  Use this on all data and code that need to be mapped into both
 *  copies of the page tables.  This includes the code that switches
 *  to/from userspace and all of the hardware structures that are
 *  virtually-addressed and needed in userspace like the interrupt
 *  table.
 */
extern int kaiser_add_mapping(unsigned long addr, unsigned long size,
			      pteval_t flags);

/**
 *  kaiser_add_mapping_cpu_entry - map the cpu entry area
 *  @cpu: the CPU for which the entry area is being mapped
 */
extern void kaiser_add_mapping_cpu_entry(int cpu);

/**
 *  kaiser_remove_mapping - remove a kernel mapping from the userpage tables
 *  @addr: the start address of the range
 *  @size: the size of the range
 */
extern void kaiser_remove_mapping(unsigned long start, unsigned long size);

/**
 *  kaiser_init - Initialize the shadow mapping
 *
 *  Most parts of the shadow mapping can be mapped upon boot
 *  time.  Only per-process things like the thread stacks
 *  or a new LDT have to be mapped at runtime.  These boot-
 *  time mappings are permanent and never unmapped.
 */
extern void kaiser_init(void);

/**
 * kaiser_early_init - Check if PTI can be enabled
 * @preset: Preset X86_FEATURE_PTI_SUPPORT bit even earlier.
 */
extern void kaiser_early_init(bool preset);

extern bool is_kaiser_pgd(pgd_t *pgd);

extern int kaiser_enabled;
static __always_inline bool kaiser_active(void)
{
	return percpu_read(kaiser_enabled_pcp);
}

#else
static inline void kaiser_add_mapping_cpu_entry(int cpu) {}
#endif

#endif /* __ASSEMBLY__ */

#endif /* _ASM_X86_KAISER_H */
