/*
	Copyright (C) 2004 - 2009 Ivo van Doorn <IvDoorn@gmail.com>
	<http://rt2x00.serialmonkey.com>

	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; either version 2 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program; if not, see <http://www.gnu.org/licenses/>.
 */

/*
	Module: rt2x00pci
	Abstract: Data structures for the rt2x00pci module.
 */

#ifndef RT2X00PCI_H
#define RT2X00PCI_H

#include <linux/io.h>
#include <linux/pci.h>

/*
 * PCI driver handlers.
 */
int rt2x00pci_probe(struct pci_dev *pci_dev, const struct rt2x00_ops *ops);
void rt2x00pci_remove(struct pci_dev *pci_dev);

extern const struct dev_pm_ops rt2x00pci_pm_ops;

#endif /* RT2X00PCI_H */
