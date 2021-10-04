// SPDX-License-Identifier: GPL-2.0 OR Linux-OpenIB
/* Copyright (c) 2020, Mellanox Technologies inc.  All rights reserved. */

#include "en/devlink.h"
#include "eswitch.h"
#include "en_rep.h"

static void
mlx5e_devlink_get_port_parent_id(struct mlx5_core_dev *dev, struct netdev_phys_item_id *ppid)
{
	u64 parent_id;

	parent_id = mlx5_query_nic_system_image_guid(dev);
	ppid->id_len = sizeof(parent_id);
	memcpy(ppid->id, &parent_id, sizeof(parent_id));
}

int mlx5e_devlink_port_register(struct mlx5e_priv *priv)
{
	struct devlink *devlink = priv_to_devlink(priv->mdev);
	struct mlx5_core_dev *mdev = priv->mdev;
	struct devlink_port_attrs attrs = {};
	struct netdev_phys_item_id ppid = {};
	unsigned int dl_port_index;

	if (!mlx5_core_is_sf(mdev))
		return 0; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	if (mlx5_core_is_pf(priv->mdev)) {
		attrs.flavour = DEVLINK_PORT_FLAVOUR_PHYSICAL;
		attrs.phys.port_number = PCI_FUNC(priv->mdev->pdev->devfn);
		if (MLX5_ESWITCH_MANAGER(priv->mdev)) {
			mlx5e_devlink_get_port_parent_id(priv->mdev, &ppid);
			memcpy(attrs.switch_id.id, ppid.id, ppid.id_len);
			attrs.switch_id.id_len = ppid.id_len;
		}
		dl_port_index = mlx5_esw_vport_to_devlink_port_index(priv->mdev,
								     MLX5_VPORT_UPLINK);
	} else {
		attrs.flavour = DEVLINK_PORT_FLAVOUR_VIRTUAL;
		dl_port_index = mlx5_esw_vport_to_devlink_port_index(priv->mdev, 0);
	}

	devlink_port_attrs_set(&priv->dl_port, &attrs);

	return devlink_port_register(devlink, &priv->dl_port, dl_port_index);
}

void mlx5e_devlink_port_type_eth_set(struct mlx5e_priv *priv)
{
	struct mlx5_core_dev *mdev = priv->mdev;

	if (!mlx5_core_is_sf(mdev))
		return; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	devlink_port_type_eth_set(&priv->dl_port, priv->netdev);
}

void mlx5e_devlink_port_unregister(struct mlx5e_priv *priv)
{
	struct mlx5_core_dev *mdev = priv->mdev;

	if (!mlx5_core_is_sf(mdev))
		return; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	devlink_port_unregister(&priv->dl_port);
}

struct devlink_port *mlx5e_get_devlink_port(struct net_device *dev)
{
	struct mlx5e_priv *priv = netdev_priv(dev);
	struct mlx5e_rep_priv *rpriv = priv->ppriv;
	struct mlx5_core_dev *mdev = priv->mdev;

	if (!netif_device_present(dev))
		return NULL;

	if (mdev->priv.eswitch && rpriv && rpriv->rep && rpriv->rep->vport)
		return mlx5_esw_offloads_devlink_port(mdev->priv.eswitch, rpriv->rep->vport);

	if (!mlx5_core_is_sf(mdev))
		return NULL; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	return &priv->dl_port;
}
