/* SPDX-License-Identifier: GPL-2.0 */
/*
 * kernel/rh_waived.c
 *
 * rh_waived cmdline parameter support.
 *
 * Copyright (C) 2024, Red Hat, Inc.  Ricardo Robaina <rrobaina@redhat.com>
 */
#include <linux/types.h>
#include <linux/init.h>
#include <linux/printk.h>
#include <linux/string.h>
#include <linux/panic.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/rh_flags.h>
#include <linux/rh_waived.h>

/*
 * RH_INSERT_WAIVED_FEAT
 *   This macro is intended to be used to insert items into the
 *   rh_waived_feat_list array. It expects to get an item from
 *   enum rh_waived_feat as its first argument, and a string
 *   holding the feature name as its second argument.
 *
 *   The feature name is also utilized as the token for the
 *   boot parameter parser.
 *
 *   Example usage:
 *   struct rh_waived_feat_item foo[RH_WAIVED_FEAT_ITEMS] = {
 *   	RH_INSERT_WAIVED_FEAT(FOO_FEAT, "foo_feat_short_str"),
 *   };
 */
#define RH_INSERT_WAIVED_FEAT(enum_item, name) \
	[(enum_item)] = {.feat_name = (name), .enabled = 0,}

/* Indicates if the rh_flag 'rh_waived' should be added. */
bool __initdata add_rh_flag = false;

struct rh_waived_feat_item {
	char *feat_name;
	unsigned int enabled;
};

/* Always use the marco RH_INSERT_WAIVED_FEAT to insert items to this array. */
struct rh_waived_feat_item rh_waived_feat_list[RH_WAIVED_FEAT_ITEMS] = {
};

/*
 * is_rh_waived() - Checks if a given waived feature has been enabled.
 *
 * @feat: waived feature.
 */
__inline__ bool is_rh_waived(enum rh_waived_feat feat)
{
	return !!rh_waived_feat_list[feat].enabled;
}
EXPORT_SYMBOL(is_rh_waived);

static int __init rh_waived_setup(char *s)
{
	int i;
	char *token;

	pr_info(KERN_CONT "rh_waived: ");

	if (!s) {
		for (i = 0; i < RH_WAIVED_FEAT_ITEMS; i++) {
			rh_waived_feat_list[i].enabled = 1;
			pr_info(KERN_CONT "%s%s", rh_waived_feat_list[i].feat_name,
				i < RH_WAIVED_FEAT_ITEMS - 1 ? " " : "\n");
		}
	}

	while ((token = strsep(&s, ",")) != NULL) {
		for (i = 0; i < RH_WAIVED_FEAT_ITEMS; i++) {
			if (!strcmp(token, rh_waived_feat_list[i].feat_name)) {
				rh_waived_feat_list[i].enabled = 1;
				pr_info(KERN_CONT "%s%s", rh_waived_feat_list[i].feat_name,
					i < RH_WAIVED_FEAT_ITEMS - 1 ? " " : "\n");
			}
		}
	}

	add_rh_flag = true;

	return 0;
}
early_param("rh_waived", rh_waived_setup);

/*
 * rh_flags is initialized at subsys_initcall, calling rh_add_flag()
 * from rh_waived_setup() would result in a can't boot situation.
 * Deffering the inclusion 'rh_waived' rh_flag to late_initcall to
 * avoid this issue.
 */
static int __init __add_rh_flag(void)
{
	if (add_rh_flag)
		rh_add_flag("rh_waived");

	return 0;
}
late_initcall(__add_rh_flag);
