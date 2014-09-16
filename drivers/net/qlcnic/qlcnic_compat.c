#include "qlcnic.h"

#ifdef CONFIG_QLCNIC_SRIOV
#ifndef pci_vfs_assigned
int pci_vfs_assigned(struct pci_dev *dev)
{
	unsigned int vfs_assigned = 0;
	struct pci_dev *vfdev;
	unsigned short dev_id;
	int pos;

	pos = pci_find_ext_capability(dev, PCI_EXT_CAP_ID_SRIOV);
	if (!dev->is_physfn)
		return 0;

	pci_read_config_word(dev, pos + PCI_SRIOV_VF_DID, &dev_id);
	vfdev = pci_get_device(dev->vendor, dev_id, NULL);
	while (vfdev) {
		if (vfdev->is_virtfn && (vfdev->physfn == dev) &&
		    (vfdev->dev_flags & PCI_DEV_FLAGS_ASSIGNED))
			vfs_assigned++;

		vfdev = pci_get_device(dev->vendor, dev_id, vfdev);
	}
	return vfs_assigned;
}
#endif
#endif
