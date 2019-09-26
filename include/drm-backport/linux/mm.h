/* SPDX-License-Identifier: GPL-2.0 */

/*
 * Compatibility shim to avoid backporting the following commits:
 * 9705bea5f833 ("mm: convert zone->managed_pages to atomic variable")
 * ca79b0c211af ("mm: convert totalram_pages and totalhigh_pages variables to atomic")
 */

#ifndef _RH_DRM_BACKPORT_LINUX_MM_H
#define _RH_DRM_BACKPORT_LINUX_MM_H

#include_next <linux/mm.h>

#ifdef RH_DRM_BACKPORT

#define zone_managed_pages(x) ((x)->managed_pages)
#define totalram_pages() totalram_pages

#endif /* RH_DRM_BACKPORT */
#endif /* _RH_DRM_BACKPORT_LINUX_MM_H */
