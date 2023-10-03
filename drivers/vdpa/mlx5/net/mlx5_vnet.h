/* SPDX-License-Identifier: GPL-2.0 OR Linux-OpenIB */
/* Copyright (c) 2022, NVIDIA CORPORATION & AFFILIATES. All rights reserved. */

#ifndef __MLX5_VNET_H__
#define __MLX5_VNET_H__

#include "mlx5_vdpa.h"

#define to_mlx5_vdpa_ndev(__mvdev)                                             \
	container_of(__mvdev, struct mlx5_vdpa_net, mvdev)
#define to_mvdev(__vdev) container_of((__vdev), struct mlx5_vdpa_dev, vdev)

struct mlx5_vdpa_net_resources {
	u32 tisn;
	u32 tdn;
	u32 tirn;
	u32 rqtn;
	bool valid;
};

#define MLX5_VDPA_IRQ_NAME_LEN 32

struct mlx5_vdpa_irq_pool_entry {
	struct msi_map map;
	bool used;
	char name[MLX5_VDPA_IRQ_NAME_LEN];
	void *dev_id;
};

struct mlx5_vdpa_irq_pool {
	int num_ent;
	struct mlx5_vdpa_irq_pool_entry *entries;
};

struct mlx5_vdpa_net {
	struct mlx5_vdpa_dev mvdev;
	struct mlx5_vdpa_net_resources res;
	struct virtio_net_config config;
	struct mlx5_vdpa_virtqueue *vqs;
	struct vdpa_callback *event_cbs;

	/* Serialize vq resources creation and destruction. This is required
	 * since memory map might change and we need to destroy and create
	 * resources while driver in operational.
	 */
	struct rw_semaphore reslock;
	struct mlx5_flow_table *rxft;
	struct mlx5_flow_handle *rx_rule_ucast;
	struct mlx5_flow_handle *rx_rule_mcast;
	bool setup;
	u32 cur_num_vqs;
	u32 rqt_size;
	bool nb_registered;
	struct notifier_block nb;
	struct vdpa_callback config_cb;
	struct mlx5_vdpa_wq_ent cvq_ent;
	struct mlx5_vdpa_irq_pool irqp;
};

#endif /* __MLX5_VNET_H__ */
