/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_X86_DEVICE_H
#define _ASM_X86_DEVICE_H

struct dev_archdata {
#ifdef CONFIG_IOMMU_API
	RH_KABI_DEPRECATE(void *, iommu) /* hook for IOMMU specific extension */
#endif
#ifdef CONFIG_STA2X11
	bool is_sta2x11;
#endif
};

struct pdev_archdata {
};

#endif /* _ASM_X86_DEVICE_H */
