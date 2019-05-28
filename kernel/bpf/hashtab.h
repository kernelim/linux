/* Copyright (c) 2019 SUSE, https://www.suse.com/
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of version 2 of the GNU General Public
 * License as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details.
 */

#include <linux/bpf.h>

/* Add this function to avoid adding an extra member to bpf_map_ops */
void *suse_htab_lru_map_lookup_elem_sys(struct bpf_map *map, void *key);
