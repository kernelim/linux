#ifndef __SDHCI_PCI_H
#define __SDHCI_PCI_H

/*
 * PCI registers
 */

#define PCI_SDHCI_IFPIO			0x00
#define PCI_SDHCI_IFDMA			0x01
#define PCI_SDHCI_IFVENDOR		0x02

#define PCI_SLOT_INFO			0x40	/* 8 bits */
#define  PCI_SLOT_INFO_SLOTS(x)		((x >> 4) & 7)
#define  PCI_SLOT_INFO_FIRST_BAR_MASK	0x07

#define MAX_SLOTS			8

struct sdhci_pci_chip;
struct sdhci_pci_slot;

struct sdhci_pci_fixes {
	unsigned int		quirks;

	int			(*probe)(struct sdhci_pci_chip*);

	int			(*probe_slot)(struct sdhci_pci_slot*);
	void			(*remove_slot)(struct sdhci_pci_slot*, int);

	int			(*suspend)(struct sdhci_pci_chip*,
					pm_message_t);
	int			(*resume)(struct sdhci_pci_chip*);
};

struct sdhci_pci_slot {
	struct sdhci_pci_chip	*chip;
	struct sdhci_host	*host;

	int			pci_bar;
};

struct sdhci_pci_chip {
	struct pci_dev		*pdev;

	unsigned int		quirks;
	const struct sdhci_pci_fixes *fixes;

	int			num_slots;	/* Slots on controller */
	struct sdhci_pci_slot	*slots[MAX_SLOTS]; /* Pointers to host slots */
};

#endif /* __SDHCI_PCI_H */
