/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rh_flags.h -- Red Hat flags tracking
 *
 * Copyright (c) 2018 Red Hat, Inc. -- Jiri Benc <jbenc@redhat.com>
 *
 * The intent of the flag tracking is to provide better and more focused
 * support. Only those flags that are of a special interest for customer
 * support should be tracked.
 *
 * THE FLAGS DO NOT EXPRESS ANY SUPPORT POLICIES.
 */

#ifndef _LINUX_RH_FLAGS_H
#define _LINUX_RH_FLAGS_H

#if defined CONFIG_RHEL_DIFFERENCES
bool __rh_add_flag(const char *flag_name);
void rh_print_flags(void);

#define rh_add_flag(flag_name)						\
({									\
	static bool __mark_once __read_mostly;				\
	bool __ret_mark_once = !__mark_once;				\
									\
	if (!__mark_once)						\
		__mark_once = __rh_add_flag(flag_name);			\
	unlikely(__ret_mark_once);					\
})
#else
void rh_print_flags(void) { };
void rh_add_flag(const char *flag_name) { };
#endif
#endif
