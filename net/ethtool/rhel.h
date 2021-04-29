// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * net/core/rhel.h - RHEL specific helpers for preserving KABI
 *
 * Copyright (c) 2020 Ivan Vecera <ivecera@redhat.com>
 *
 * This file contains stuff used for backward compatibility with
 * older binary drivers.
 */

#ifndef _NET_ETHTOOL_RHEL_H
#define _NET_ETHTOOL_RHEL_H

#include <linux/types.h>
#include <linux/bitmap.h>
#include <linux/errno.h>
#include <linux/ethtool.h>
#include <linux/netdevice.h>

/* RHEL: RHEL-8.0 knows only 51 link modes so its bitmaps used
 * in ethtool_link_ksettings are array of longs with just 1 item.
 * The RHEL code uses more link modes so the size of fields
 * supported, advertising and lp_advertising are larger so
 * the current struct ethtool_link_ksettings cannot be used
 * for drivers compiled against RHEL-8.0.
 * We need to declare a compatibility structure that will
 * be used for these old drivers.
 */
#define __ETHTOOL_DECLARE_LINK_MODE_MASK_RH80(name)	\
	DECLARE_BITMAP(name, __ETHTOOL_LINK_MODE_LAST_RH80 + 1)

struct ethtool_link_ksettings_rh80 {
	struct ethtool_link_settings base;
	struct {
		__ETHTOOL_DECLARE_LINK_MODE_MASK_RH80(supported);
		__ETHTOOL_DECLARE_LINK_MODE_MASK_RH80(advertising);
		__ETHTOOL_DECLARE_LINK_MODE_MASK_RH80(lp_advertising);
	} link_modes;
};

/* RHEL: Helper function to check whether a driver implements
 * ethtool_ops->get_link_ksettings() callback or its older
 * variant used in RHEL-8.0.
 */
static inline
bool __rh_has_get_link_ksettings(struct net_device *dev)
{
	return (dev->ethtool_ops->get_link_ksettings ||
		dev->ethtool_ops->get_link_ksettings_rh80);
}

/* RHEL: Helper function to check whether a driver implements
 * ethtool_ops->set_link_ksettings() callback or its older
 * variant used in RHEL-8.0.
 */
static inline
bool __rh_has_set_link_ksettings(struct net_device *dev)
{
	return (dev->ethtool_ops->set_link_ksettings ||
		dev->ethtool_ops->set_link_ksettings_rh80);
}

/* RHEL: Helper function to call ethtool_ops->get_link_ksettings()
 * callback or its older variant used RHEL-8.0 depending on what
 * the driver implements.
 *
 * Newer callback is called directly and link_ksettings parameter
 * is passed through.
 * For older callback a temporary storage is used and its content
 * is then translated for caller.
 */
static inline
int __rh_call_get_link_ksettings(struct net_device *dev,
				 struct ethtool_link_ksettings *link_ksettings)
{
	int err = -ENOTSUPP;

	if (dev->ethtool_ops->get_link_ksettings) {
		err = dev->ethtool_ops->get_link_ksettings(dev, link_ksettings);
	} else if (dev->ethtool_ops->get_link_ksettings_rh80) {
		struct ethtool_link_ksettings_rh80 tmp;

		memset(&tmp, 0, sizeof(tmp));
		err = dev->ethtool_ops->get_link_ksettings_rh80(dev, &tmp);
		if (!err) {
			link_ksettings->base = tmp.base;
			bitmap_zero(link_ksettings->link_modes.supported,
				    __ETHTOOL_LINK_MODE_MASK_NBITS - 1);
			bitmap_copy(link_ksettings->link_modes.supported,
				    tmp.link_modes.supported,
				    __ETHTOOL_LINK_MODE_LAST_RH80);
			bitmap_zero(link_ksettings->link_modes.advertising,
				    __ETHTOOL_LINK_MODE_MASK_NBITS - 1);
			bitmap_copy(link_ksettings->link_modes.advertising,
				    tmp.link_modes.advertising,
				    __ETHTOOL_LINK_MODE_LAST_RH80);
			bitmap_zero(link_ksettings->link_modes.lp_advertising,
				    __ETHTOOL_LINK_MODE_MASK_NBITS - 1);
			bitmap_copy(link_ksettings->link_modes.lp_advertising,
				    tmp.link_modes.lp_advertising,
				    __ETHTOOL_LINK_MODE_LAST_RH80);
		}
	}

	return err;
}

/* RHEL: Helper function to call ethtool_ops->set_link_ksettings()
 * callback or its older variant used RHEL-8.0 depending on what
 * the driver implements.
 *
 * Newer callback is called directly and link_ksettings parameter
 * is passed through.
 * For older callback a temporary storage is used and its content
 * is filled from input buffer (link modes bitmaps truncated).
 */
static inline
int __rh_call_set_link_ksettings(struct net_device *dev,
				 const struct ethtool_link_ksettings *link_ksettings)
{
	int err = -ENOTSUPP;

	if (dev->ethtool_ops->set_link_ksettings) {
		err = dev->ethtool_ops->set_link_ksettings(dev, link_ksettings);
	} else if (dev->ethtool_ops->set_link_ksettings_rh80) {
		struct ethtool_link_ksettings_rh80 tmp;

		/* Copy only link modes that are known for RHEL-8.0 based
		 * drivers.
		 */
		tmp.base = link_ksettings->base;
		bitmap_copy(tmp.link_modes.supported,
			    link_ksettings->link_modes.supported,
			    __ETHTOOL_LINK_MODE_LAST_RH80);
		bitmap_copy(tmp.link_modes.advertising,
			    link_ksettings->link_modes.advertising,
			    __ETHTOOL_LINK_MODE_LAST_RH80);
		bitmap_copy(tmp.link_modes.lp_advertising,
			    link_ksettings->link_modes.lp_advertising,
			    __ETHTOOL_LINK_MODE_LAST_RH80);

		err = dev->ethtool_ops->set_link_ksettings_rh80(dev, &tmp);
	}

	return err;
}

#endif /* _NET_ETHTOOL_RHEL_H */
