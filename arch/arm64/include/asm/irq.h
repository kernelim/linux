/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __ASM_IRQ_H
#define __ASM_IRQ_H

#ifndef __ASSEMBLER__


/*
 * RHEL-9.2-only -- increase max NR_IRQS from 64+8192 default
 *    for large, HPC arm64 kernels with 64K page-size
 */
#if defined(CONFIG_ARM_GIC_V3_ITS) && defined(CONFIG_ARM64_64K_PAGES)
#define  NR_IRQS  (1 << 19)
#endif

#include <asm-generic/irq.h>

struct pt_regs;

int set_handle_irq(void (*handle_irq)(struct pt_regs *));
#define set_handle_irq	set_handle_irq
int set_handle_fiq(void (*handle_fiq)(struct pt_regs *));

static inline int nr_legacy_irqs(void)
{
	return 0;
}

#endif /* !__ASSEMBLER__ */
#endif
