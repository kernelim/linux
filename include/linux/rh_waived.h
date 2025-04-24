/* SPDX-License-Identifier: GPL-2.0 */
/*
 * include/linux/rh_waived.h
 *
 * rh_waived cmdline parameter interface.
 *
 * Copyright (C) 2024, Red Hat, Inc.  Ricardo Robaina <rrobaina@redhat.com>
 */
#ifndef _RH_WAIVED_H
#define _RH_WAIVED_H

enum rh_waived_feat {
	/* RH_WAIVED_FEAT_ITEMS must always be the last item in the enum */
	RH_WAIVED_FEAT_ITEMS,
};

bool is_rh_waived(enum rh_waived_feat feat);

#endif /* _RH_WAIVED_H */
