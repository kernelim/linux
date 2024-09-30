/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Clang Control Flow Integrity (CFI) support.
 *
 * Copyright (C) 2021 Google LLC
 */
#ifndef _LINUX_CFI_H
#define _LINUX_CFI_H

#include <asm/cfi.h>

#ifndef cfi_get_offset
static inline int cfi_get_offset(void)
{
	return 0;
}
#endif

#ifdef CONFIG_CFI_CLANG
typedef void (*cfi_check_fn)(uint64_t id, void *ptr, void *diag);

/* Compiler-generated function in each module, and the kernel */
extern void __cfi_check(uint64_t id, void *ptr, void *diag);

#endif /* CONFIG_CFI_CLANG */

#ifndef CFI_NOSEAL
#define CFI_NOSEAL(x)
#endif

#endif /* _LINUX_CFI_H */
