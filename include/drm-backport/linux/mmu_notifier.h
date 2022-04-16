/* SPDX-License-Identifier: GPL-2.0 */

#ifndef __RH_DRM_BACKPORT_MMU_NOTIFIER_H__
#define __RH_DRM_BACKPORT_MMU_NOTIFIER_H__

#ifdef RH_DRM_BACKPORT
#define RH_MMU_NOTIFIER_V2
#endif

#include_next <linux/mmu_notifier.h>
#endif
