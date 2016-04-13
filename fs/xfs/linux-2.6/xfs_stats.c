/*
 * Copyright (c) 2000-2003,2005 Silicon Graphics, Inc.
 * All Rights Reserved.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it would be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write the Free Software Foundation,
 * Inc.,  51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */
#include "xfs.h"
#include <linux/proc_fs.h>

struct xstats xfsstats;

static int counter_val(struct xfsstats __percpu *stats, int idx)
{
	int val = 0, cpu;

	for_each_possible_cpu(cpu)
		val += *(((__u32 *)per_cpu_ptr(stats, cpu) + idx));
	return val;
}

int xfs_stats_format(struct xfsstats __percpu *stats, char *buf)
{
	int		i, j;
	int		len = 0;
	__uint64_t	xs_xstrat_bytes = 0;
	__uint64_t	xs_write_bytes = 0;
	__uint64_t	xs_read_bytes = 0;

	static const struct xstats_entry {
		char	*desc;
		int	endpoint;
	} xstats[] = {
		{ "extent_alloc",	XFSSTAT_END_EXTENT_ALLOC	},
		{ "abt",		XFSSTAT_END_ALLOC_BTREE		},
		{ "blk_map",		XFSSTAT_END_BLOCK_MAPPING	},
		{ "bmbt",		XFSSTAT_END_BLOCK_MAP_BTREE	},
		{ "dir",		XFSSTAT_END_DIRECTORY_OPS	},
		{ "trans",		XFSSTAT_END_TRANSACTIONS	},
		{ "ig",			XFSSTAT_END_INODE_OPS		},
		{ "log",		XFSSTAT_END_LOG_OPS		},
		{ "push_ail",		XFSSTAT_END_TAIL_PUSHING	},
		{ "xstrat",		XFSSTAT_END_WRITE_CONVERT	},
		{ "rw",			XFSSTAT_END_READ_WRITE_OPS	},
		{ "attr",		XFSSTAT_END_ATTRIBUTE_OPS	},
		{ "icluster",		XFSSTAT_END_INODE_CLUSTER	},
		{ "vnodes",		XFSSTAT_END_VNODE_OPS		},
		{ "buf",		XFSSTAT_END_BUF			},
		{ "abtb2",		XFSSTAT_END_ABTB_V2		},
		{ "abtc2",		XFSSTAT_END_ABTC_V2		},
		{ "bmbt2",		XFSSTAT_END_BMBT_V2		},
		{ "ibt2",		XFSSTAT_END_IBT_V2		},
	};

	/* Loop over all stats groups */

	for (i = j = 0; i < ARRAY_SIZE(xstats); i++) {
		len += snprintf(buf + len, PATH_MAX - len, "%s",
				xstats[i].desc);
		/* inner loop does each group */
		for (; j < xstats[i].endpoint; j++)
			len += snprintf(buf + len, PATH_MAX - len, " %u",
					counter_val(stats, j));
		len += snprintf(buf + len, PATH_MAX - len, "\n");
	}
	/* extra precision counters */
	for_each_possible_cpu(i) {
		xs_xstrat_bytes += per_cpu_ptr(stats, i)->xs_xstrat_bytes;
		xs_write_bytes += per_cpu_ptr(stats, i)->xs_write_bytes;
		xs_read_bytes += per_cpu_ptr(stats, i)->xs_read_bytes;
	}

	len += snprintf(buf + len, PATH_MAX-len, "xpc %Lu %Lu %Lu\n",
			xs_xstrat_bytes, xs_write_bytes, xs_read_bytes);
	len += snprintf(buf + len, PATH_MAX-len, "debug %u\n",
#if defined(DEBUG)
		1);
#else
		0);
#endif

	return len;
}

void xfs_stats_clearall(struct xfsstats __percpu *stats)
{
	int		c;
	__uint32_t	vn_active;

	xfs_notice(NULL, "Clearing xfsstats");
	for_each_possible_cpu(c) {
		preempt_disable();
		/* save vn_active, it's a universal truth! */
		vn_active = per_cpu_ptr(stats, c)->vn_active;
		memset(per_cpu_ptr(stats, c), 0, sizeof(*stats));
		per_cpu_ptr(stats, c)->vn_active = vn_active;
		preempt_enable();
	}
}

#ifdef CONFIG_PROC_FS
int
xfs_init_procfs(void)
{
	if (!proc_mkdir("fs/xfs", NULL))
		goto out;

	if (!proc_symlink("fs/xfs/stat", NULL,
			  "/sys/fs/xfs/stats/stats"))
		goto out_remove_entry;

	return 0;

 out_remove_entry:
	remove_proc_entry("fs/xfs", NULL);
 out:
	return -ENOMEM;
}

void
xfs_cleanup_procfs(void)
{
	remove_proc_entry("fs/xfs/stat", NULL);
	remove_proc_entry("fs/xfs", NULL);
}
#endif /* CONFIG_PROC_FS */
