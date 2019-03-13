/* SPDX-License-Identifier: GPL-2.0 */
/*
 * rh_features.h -- Red Hat features tracking
 *
 * Copyright (c) 2018 Red Hat, Inc. -- Jiri Benc <jbenc@redhat.com>
 *
 * The intent of the feature tracking is to provide better and more focused
 * support. Only those features that are of a special interest for customer
 * support should be tracked. The feature flags do not express any support
 * policy.
 */

#ifndef _LINUX_RH_FEATURES_H
#define _LINUX_RH_FEATURES_H

bool __rh_mark_used_feature(const char *feature_name);
void rh_print_used_features(void);

#define rh_mark_used_feature(feature_name)				\
({									\
	static bool __mark_once __read_mostly;				\
	bool __ret_mark_once = !__mark_once;				\
									\
	if (!__mark_once)						\
		__mark_once = __rh_mark_used_feature(feature_name);	\
	unlikely(__ret_mark_once);					\
})

#endif
