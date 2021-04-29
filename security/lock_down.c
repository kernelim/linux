/* Lock down the kernel
 *
 * Copyright (C) 2016 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#include <linux/security.h>
#include <linux/export.h>
#include <linux/sched.h>
#include <linux/efi.h>
#include <asm/setup.h>
#ifdef CONFIG_S390
#include <asm/ipl.h>
#endif
#ifdef CONFIG_PPC64
#include <asm/secure_boot.h>
#endif

#ifndef CONFIG_LOCK_DOWN_MANDATORY
static __ro_after_init bool kernel_locked_down;
#else
#define kernel_locked_down true
#endif

static const char *const lockdown_levels[] = { "none", "integrity" };

/*
 * Put the kernel into lock-down mode.
 */
static void __init lock_kernel_down(const char *where)
{
#ifndef CONFIG_LOCK_DOWN_MANDATORY
	if (!kernel_locked_down) {
		kernel_locked_down = true;
		pr_notice("Kernel is locked down from %s; see man kernel_lockdown.7\n",
			  where);
	}
#endif
}

static int __init lockdown_param(char *ignored)
{
	lock_kernel_down("command line");
	return 0;
}

early_param("lockdown", lockdown_param);

/*
 * Lock the kernel down from very early in the arch setup.  This must happen
 * prior to things like ACPI being initialised.
 */
void __init init_lockdown(void)
{
#ifdef CONFIG_LOCK_DOWN_MANDATORY
	pr_notice("Kernel is locked down from config; see man kernel_lockdown.7\n");
#endif
#ifdef CONFIG_LOCK_DOWN_IN_EFI_SECURE_BOOT
	if (efi_enabled(EFI_SECURE_BOOT))
		lock_kernel_down("EFI secure boot");
#endif
#ifdef CONFIG_S390
	if (ipl_get_secureboot())
		lock_kernel_down("Secure IPL");
#endif
#ifdef CONFIG_PPC64
	if (is_ppc_secureboot_enabled())
		lock_kernel_down("Power secure boot");
#endif
}

/**
 * kernel_is_locked_down - Find out if the kernel is locked down
 * @what: Tag to use in notice generated if lockdown is in effect
 */
bool __kernel_is_locked_down(const char *what, bool first)
{
	if (what && first && kernel_locked_down)
		pr_notice("Lockdown: %s: %s is restricted; see man kernel_lockdown.7\n",
			  current->comm, what);
	return kernel_locked_down;
}
EXPORT_SYMBOL(__kernel_is_locked_down);

static ssize_t lockdown_read(struct file *filp, char __user *buf, size_t count,
			     loff_t *ppos)
{
	char temp[32];

	if (__kernel_is_locked_down(NULL, false))
		sprintf(temp, "%s [%s]\n", lockdown_levels[0], lockdown_levels[1]);
	else
		sprintf(temp, "[%s] %s\n", lockdown_levels[0], lockdown_levels[1]);

	return simple_read_from_buffer(buf, count, ppos, temp, strlen(temp));
}

static const struct file_operations lockdown_ops = {
	.read  = lockdown_read,
};

static int __init lockdown_secfs_init(void)
{
	struct dentry *dentry;

	dentry = securityfs_create_file("lockdown", 0444, NULL, NULL,
					&lockdown_ops);
	return PTR_ERR_OR_ZERO(dentry);
}

core_initcall(lockdown_secfs_init);
