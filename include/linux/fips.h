/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _FIPS_H
#define _FIPS_H

#ifdef CONFIG_CRYPTO_FIPS
extern int fips_enabled;
extern struct atomic_notifier_head fips_fail_notif_chain;

void fips_fail_notify(void);
/*
 * fips_allows - check if a not fully FIPS-compliant feature is allowed
 * via an explicit boot-time exception (rh_fips_exception=).
 * Not for fully FIPS-compliant features.
 */
int fips_allows(unsigned long feature);

#else
#define fips_enabled 0

static inline void fips_fail_notify(void) {}
static inline int fips_allows(unsigned long feature)
{
	return 1;
}

#endif

#define FIPS_EXCEPTION_WIFI_MFP	BIT(0)

#endif
