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
 * * RH_INSERT_WAIVED_ITEM
 *   This macro is intended to be used to insert items into the
 *   rh_waived_list array. It expects to get an item from
 *   enum rh_waived_items as its first argument, and a string
 *   holding the feature name as its second argument.
 *
 *   The feature name is also utilized as the token for the
 *   boot parameter parser.
 *
 *   Example usage:
 *   struct rh_waived_item foo[RH_WAIVED_FEAT_ITEMS] = {
 *     RH_INSERT_WAIVED_ITEM(FOO_FEAT, "foo_feat_short_str", "alias", RH_WAIVED_FEAT),
 *   };
 */
#define RH_INSERT_WAIVED_ITEM(enum_item, item, item_alt, class)                \
       [(enum_item)] = { .name = (item), .alias = (item_alt),          \
                         .type = (class), .waived = 0, }

/* Indicates if the rh_flag 'rh_waived' should be added. */
bool __initdata add_rh_flag = false;

typedef enum {
       RH_WAIVED_FEAT,
       RH_WAIVED_CVE,
       RH_WAIVED_ANY
} rh_waived_t;

struct rh_waived_item {
       char *name, *alias;
       rh_waived_t type;
       unsigned int waived;

};

/* Always use the marco RH_INSERT_WAIVED to insert items to this array. */
struct rh_waived_item rh_waived_list[RH_WAIVED_ITEMS] = {
	RH_INSERT_WAIVED_ITEM(CVE_2025_38085, "CVE-2025-38085",
			      "no-cve-2025-38085", RH_WAIVED_CVE),
};

/*
 * is_rh_waived() - Checks if a given item has been marked as waived.
 *
 * @item: waived item.
 */
__inline__ bool is_rh_waived(enum rh_waived_items item)
{
	return !!rh_waived_list[item].waived;
}
EXPORT_SYMBOL(is_rh_waived);

static void __init rh_waived_parser(char *s, rh_waived_t type)
{
	int i;
	char *token;

	pr_info(KERN_CONT "rh_waived: ");

	if (!s) {
		for (i = 0; i < RH_WAIVED_ITEMS; i++) {
			if (type != RH_WAIVED_ANY && rh_waived_list[i].type != type)
				continue;

			rh_waived_list[i].waived = 1;
			pr_info(KERN_CONT "%s%s", rh_waived_list[i].name,
				i < RH_WAIVED_ITEMS - 1 ? " " : "\n");
		}

		add_rh_flag = true;
		return;
	}

	while ((token = strsep(&s, ",")) != NULL) {
		for (i = 0; i < RH_WAIVED_ITEMS; i++) {
			char *alias = rh_waived_list[i].alias;

			if (type != RH_WAIVED_ANY && rh_waived_list[i].type != type)
				continue;

			if (!strcmp(token, rh_waived_list[i].name) ||
			    (alias && !strcmp(token, alias))) {
				rh_waived_list[i].waived = 1;
				pr_info(KERN_CONT "%s ", rh_waived_list[i].name);
			}
		}
	}

	pr_info(KERN_CONT "\n");
	add_rh_flag = true;
}

static int __init rh_waived_setup(char *s)
{
	/*
	 * originally, if no string was passed to the cmdline option
	 * all listed features would be waived, so we keep that same
	 * compromise with the new contract.
	 */
	if (!s || !strcmp(s, "features")) {
		rh_waived_parser(NULL, RH_WAIVED_FEAT);
		return 0;
	}

	/* waive all possible mitigations in the list */
	if (!strcmp(s, "cves")) {
		rh_waived_parser(NULL, RH_WAIVED_CVE);
		return 0;
	}

	/* otherwise, just deal with the enumerated waive list */
	rh_waived_parser(s, RH_WAIVED_ANY);

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
