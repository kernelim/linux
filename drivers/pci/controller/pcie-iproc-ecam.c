// SPDX-License-Identifier: GPL-2.0
/*
 * Copyright (C) 2018 Broadcom
 */

#include <linux/kernel.h>
#include <linux/pci.h>
#include <linux/pci-acpi.h>
#include <linux/pci-ecam.h>

#include "pcie-iproc.h"
#include "../pci.h"

#if defined(CONFIG_ACPI) && defined(CONFIG_PCI_QUIRKS)

static int iproc_pcie_ecam_init(struct pci_config_window *cfg)
{
	struct device *dev = cfg->parent;
	struct iproc_pcie *pcie;
	struct resource *res = &cfg->res;
	struct pci_host_bridge *bridge;
	int ret;

	bridge = devm_pci_alloc_host_bridge(dev, sizeof(*pcie));
	if (!bridge)
		return -ENOMEM;
	pcie = pci_host_bridge_priv(bridge);

	pcie->dev = dev;
	pcie->type = IPROC_PCIE_PAXC_V2;

	pcie->base = devm_pci_remap_cfgspace(dev, res->start,
					     resource_size(res));
	if (!pcie->base) {
		dev_err(dev, "unable to map controller registers\n");
		return -ENOMEM;
	}
	pcie->base_addr = res->start;
	cfg->priv = pcie;

	ret = iproc_pcie_rev_init(pcie);
	if (ret) {
		dev_err(dev, "unable to initialize iProc PCIe controller\n");
		return ret;
	}

	return 0;
}

struct pci_ecam_ops iproc_pcie_paxcv2_ecam_ops = {
	.init = iproc_pcie_ecam_init,
	.pci_ops = {
		.map_bus = iproc_pcie_bus_map_cfg_bus,
		.read = iproc_pcie_config_read32,
		.write = iproc_pcie_config_write32,
	}
};

#endif
