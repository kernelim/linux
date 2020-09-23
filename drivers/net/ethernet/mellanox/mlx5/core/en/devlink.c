// SPDX-License-Identifier: GPL-2.0 OR Linux-OpenIB
/* Copyright (c) 2020, Mellanox Technologies inc.  All rights reserved. */

#include "en/devlink.h"

int mlx5e_devlink_port_register(struct mlx5e_priv *priv)
{
	struct devlink *devlink = priv_to_devlink(priv->mdev);

	return 0; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	if (mlx5_core_is_pf(priv->mdev))
		devlink_port_attrs_set(&priv->dl_port,
				       DEVLINK_PORT_FLAVOUR_PHYSICAL,
				       PCI_FUNC(priv->mdev->pdev->devfn),
				       false, 0,
				       NULL, 0);
	else
		devlink_port_attrs_set(&priv->dl_port,
				       DEVLINK_PORT_FLAVOUR_VIRTUAL,
				       0, false, 0, NULL, 0);

	return devlink_port_register(devlink, &priv->dl_port, 1);
}

void mlx5e_devlink_port_type_eth_set(struct mlx5e_priv *priv)
{
	return; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	devlink_port_type_eth_set(&priv->dl_port, priv->netdev);
}

void mlx5e_devlink_port_unregister(struct mlx5e_priv *priv)
{
	return; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	devlink_port_unregister(&priv->dl_port);
}

struct devlink_port *mlx5e_get_devlink_port(struct net_device *dev)
{
	struct mlx5e_priv *priv = netdev_priv(dev);

	return NULL; /* RHEL-only: Disable 'devlink port' support for non-switchdev mode*/

	return &priv->dl_port;
}
