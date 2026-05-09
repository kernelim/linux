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

enum rh_waived_items {
	CVE_2025_38085,
	/* RH_WAIVED_ITEMS must always be the last item in the enum */
	RH_WAIVED_ITEMS,
};

bool is_rh_waived(enum rh_waived_items feat);

#endif /* _RH_WAIVED_H */
