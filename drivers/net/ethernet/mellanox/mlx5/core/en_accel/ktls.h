/* SPDX-License-Identifier: GPL-2.0 OR Linux-OpenIB */
/* Copyright (c) 2019 Mellanox Technologies. */

#ifndef __MLX5E_KTLS_H__
#define __MLX5E_KTLS_H__

#include "en.h"
#include "accel/tls.h"

#ifdef CONFIG_MLX5_EN_TLS

void mlx5e_ktls_build_netdev(struct mlx5e_priv *priv);
int mlx5e_ktls_init_rx(struct mlx5e_priv *priv);
void mlx5e_ktls_cleanup_rx(struct mlx5e_priv *priv);
int mlx5e_ktls_set_feature_rx(struct net_device *netdev, bool enable);

static inline bool mlx5e_accel_is_ktls_tx(struct mlx5_core_dev *mdev)
{
	return !is_kdump_kernel() &&
		mlx5_accel_is_ktls_tx(mdev);
}

static inline bool mlx5e_accel_is_ktls_rx(struct mlx5_core_dev *mdev)
{
	return !is_kdump_kernel() &&
		mlx5_accel_is_ktls_rx(mdev);
}

static inline bool mlx5e_accel_is_ktls_device(struct mlx5_core_dev *mdev)
{
	return !is_kdump_kernel() &&
		mlx5_accel_is_ktls_device(mdev);
}

#else

static inline void mlx5e_ktls_build_netdev(struct mlx5e_priv *priv)
{
}

static inline int mlx5e_ktls_init_rx(struct mlx5e_priv *priv)
{
	return 0;
}

static inline void mlx5e_ktls_cleanup_rx(struct mlx5e_priv *priv)
{
}

static inline int mlx5e_ktls_set_feature_rx(struct net_device *netdev, bool enable)
{
	netdev_warn(netdev, "kTLS is not supported\n");
	return -EOPNOTSUPP;
}

static inline bool mlx5e_accel_is_ktls_tx(struct mlx5_core_dev *mdev) { return false; }
static inline bool mlx5e_accel_is_ktls_rx(struct mlx5_core_dev *mdev) { return false; }
static inline bool mlx5e_accel_is_ktls_device(struct mlx5_core_dev *mdev) { return false; }

#endif

#endif /* __MLX5E_TLS_H__ */
