/* SPDX-License-Identifier: GPL-2.0 */

/* TEMPORARY!! compatibility shim for the following commits:
 * 9285ec4c8b61 ("timekeeping: Use proper clock specifier names in functions")
 *
 * TODO: This should be removed before the final backport submission, and
 * instead replaced by a system-wide replacement of RHEL's kernel tree so that
 * our timekeeping functions match upstreams, since it's easy and there's no
 * functional changes.
 */
#ifndef _RH_DRM_BACKPORT_TIMEKEEPING_H
#define _RH_DRM_BACKPORT_TIMEKEEPING_H

#include_next <linux/timekeeping.h>

#ifdef RH_DRM_BACKPORT

#define ktime_get_boottime_ns() ktime_get_boot_ns()
#define ktime_get_clocktai_ns() ktime_get_tai_ns()

#endif /* RH_DRM_BACKPORT */
#endif /* _RH_DRM_BACKPORT_TIMEKEEPING_H */
