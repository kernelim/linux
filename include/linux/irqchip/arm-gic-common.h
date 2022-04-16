/*
 * include/linux/irqchip/arm-gic-common.h
 *
 * Copyright (C) 2016 ARM Limited, All Rights Reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 */
#ifndef __LINUX_IRQCHIP_ARM_GIC_COMMON_H
#define __LINUX_IRQCHIP_ARM_GIC_COMMON_H

#include <linux/irqchip/arm-vgic-info.h>

#define GICD_INT_DEF_PRI		0xa0
#define GICD_INT_DEF_PRI_X4		((GICD_INT_DEF_PRI << 24) |\
					(GICD_INT_DEF_PRI << 16) |\
					(GICD_INT_DEF_PRI << 8) |\
					GICD_INT_DEF_PRI)

struct irq_domain;
struct fwnode_handle;
int gicv2m_init(struct fwnode_handle *parent_handle,
		struct irq_domain *parent);

#endif /* __LINUX_IRQCHIP_ARM_GIC_COMMON_H */
