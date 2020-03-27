/* SPDX-License-Identifier: GPL-2.0 */

/*
 * Compatability shim to avoid backporting the following commits:
 * 1f58bb18f6f2 ("mount_pseudo(): drop 'name' argument, switch to d_make_root()")
 *
 * Note that this only works because mount_pseudo() is called from only one
 * place in DRM. If that changes, we'll need a different solution.
 */

#ifndef _RH_DRM_BACKPORT_FS_H
#define _RH_DRM_BACKPORT_FS_H

#include_next <linux/fs.h>

#ifdef RH_DRM_BACKPORT

#define mount_pseudo(fs_type, ops, dops, magic) \
	mount_pseudo(fs_type, "drm:", ops, dops, magic)

#endif /* RH_DRM_BACKPORT */
#endif /* _RH_DRM_BACKPORT_FS_H */
