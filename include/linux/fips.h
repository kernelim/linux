/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _FIPS_H
#define _FIPS_H

#include <generated/utsrelease.h>

#ifdef CONFIG_CRYPTO_FIPS
extern int fips_enabled;
extern struct atomic_notifier_head fips_fail_notif_chain;

#define FIPS_MODULE_NAME CONFIG_CRYPTO_FIPS_NAME
#ifdef CONFIG_CRYPTO_FIPS_CUSTOM_VERSION
#define FIPS_MODULE_VERSION CONFIG_CRYPTO_FIPS_VERSION
#else
#define FIPS_MODULE_VERSION UTS_RELEASE
#endif

void fips_fail_notify(void);

#else
#define fips_enabled 0

static inline void fips_fail_notify(void) {}

#endif

#endif
