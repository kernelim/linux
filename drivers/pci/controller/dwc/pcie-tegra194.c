// SPDX-License-Identifier: GPL-2.0+
/*
 * PCIe host controller driver for Tegra194 SoC
 *
 * Copyright (C) 2019 NVIDIA Corporation.
 *
 * Author: Vidya Sagar <vidyas@nvidia.com>
 */

#include <linux/pci-ecam.h>
#include "pcie-designware.h"

#if defined(CONFIG_ACPI) && defined(CONFIG_PCI_QUIRKS)
struct tegra194_pcie_acpi  {
	void __iomem *config_base;
	void __iomem *iatu_base;
	void __iomem *dbi_base;
};

static int tegra194_acpi_init(struct pci_config_window *cfg)
{
	struct device *dev = cfg->parent;
	struct tegra194_pcie_acpi *pcie;

	pcie = devm_kzalloc(dev, sizeof(*pcie), GFP_KERNEL);
	if (!pcie)
		return -ENOMEM;

	pcie->config_base = cfg->win;
	pcie->iatu_base = cfg->win + SZ_256K;
	pcie->dbi_base = cfg->win + SZ_512K;
	cfg->priv = pcie;

	return 0;
}

static inline void atu_reg_write(struct tegra194_pcie_acpi *pcie, int index,
				 u32 val, u32 reg)
{
	u32 offset = PCIE_GET_ATU_OUTB_UNR_REG_OFFSET(index);

	writel(val, pcie->iatu_base + offset + reg);
}

static void program_outbound_atu(struct tegra194_pcie_acpi *pcie, int index,
				 int type, u64 cpu_addr, u64 pci_addr, u64 size)
{
	atu_reg_write(pcie, index, lower_32_bits(cpu_addr),
		      PCIE_ATU_LOWER_BASE);
	atu_reg_write(pcie, index, upper_32_bits(cpu_addr),
		      PCIE_ATU_UPPER_BASE);
	atu_reg_write(pcie, index, lower_32_bits(pci_addr),
		      PCIE_ATU_LOWER_TARGET);
	atu_reg_write(pcie, index, lower_32_bits(cpu_addr + size - 1),
		      PCIE_ATU_LIMIT);
	atu_reg_write(pcie, index, upper_32_bits(pci_addr),
		      PCIE_ATU_UPPER_TARGET);
	atu_reg_write(pcie, index, type, PCIE_ATU_CR1);
	atu_reg_write(pcie, index, PCIE_ATU_ENABLE, PCIE_ATU_CR2);
}

static void __iomem *tegra194_map_bus(struct pci_bus *bus,
				      unsigned int devfn, int where)
{
	struct pci_config_window *cfg = bus->sysdata;
	struct tegra194_pcie_acpi *pcie = cfg->priv;
	u32 busdev;
	int type;

	if (bus->number < cfg->busr.start || bus->number > cfg->busr.end)
		return NULL;

	if (bus->number == cfg->busr.start) {
		if (PCI_SLOT(devfn) == 0)
			return pcie->dbi_base + where;
		else
			return NULL;
	}

	busdev = PCIE_ATU_BUS(bus->number) | PCIE_ATU_DEV(PCI_SLOT(devfn)) |
		 PCIE_ATU_FUNC(PCI_FUNC(devfn));

	if (bus->parent->number == cfg->busr.start) {
		if (PCI_SLOT(devfn) == 0)
			type = PCIE_ATU_TYPE_CFG0;
		else
			return NULL;
	} else {
		type = PCIE_ATU_TYPE_CFG1;
	}

	program_outbound_atu(pcie, PCIE_ATU_REGION_INDEX0, type,
			     cfg->res.start, busdev, SZ_256K);
	return (void __iomem *)(pcie->config_base + where);
}

struct pci_ecam_ops tegra194_pcie_ops = {
	.bus_shift	= 20,
	.init		= tegra194_acpi_init,
	.pci_ops	= {
		.map_bus	= tegra194_map_bus,
		.read		= pci_generic_config_read,
		.write		= pci_generic_config_write,
	}
};
#endif /* defined(CONFIG_ACPI) && defined(CONFIG_PCI_QUIRKS) */
