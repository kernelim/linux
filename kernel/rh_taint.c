#include <linux/kernel.h>
#include <linux/module.h>

/*
 * The following functions are used by Red Hat to indicate to users that
 * hardware and drivers are unsupported, or have limited support in RHEL major
 * and minor releases.  These functions output loud warning messages to the end
 * user and should be USED WITH CAUTION.
 *
 * Any use of these functions _MUST_ be documented in the RHEL Release Notes,
 * and have approval of management.
 */

/**
 * mark_hardware_unsupported() - Mark hardware, class, or type as unsupported.
 * @msg: Hardware name, class, or type
 *
 * Called to mark a device, class of devices, or types of devices as not having
 * support in any RHEL minor release.  This does not TAINT the kernel.  Red Hat
 * will not fix bugs against this hardware in this minor release.  Red Hat may
 * declare support in a future major or minor update release.  This cannot be
 * used to mark drivers unsupported.
 */
void mark_hardware_unsupported(const char *msg)
{
	/* Print one single message */
	pr_crit("Warning: %s - this hardware has not undergone testing by Red Hat and might not be certified. Please consult https://catalog.redhat.com for certified hardware.\n", msg);
}
EXPORT_SYMBOL(mark_hardware_unsupported);

/**
 * mark_hardware_deprecated() - Mark hardware, class, or type as deprecated.
 * @msg: Hardware name, class, or type
 *
 * Called to minimize the support status of a previously supported device in
 * a minor release.  This does not TAINT the kernel.  Marking hardware
 * deprecated is usually done in conjunction with the hardware vendor.  Future
 * RHEL major releases may not include this driver.  Driver updates and fixes
 * for this device will be limited to critical issues in future minor releases.
 */
void mark_hardware_deprecated(const char *msg)
{
	pr_crit("Warning: %s - this hardware is not recommended for new deployments. It continues to be supported in this RHEL release, but it is likely to be removed in the next major release. Driver updates and fixes for this device will be limited to critical issues. Please contact Red Hat Support or your device's hardware vendor for additional information.\n", msg);
}
EXPORT_SYMBOL(mark_hardware_deprecated);

/**
 * mark_tech_preview() - Mark driver or kernel subsystem as 'Tech Preview'
 * @msg: Driver or kernel subsystem name
 *
 * Called to minimize the support status of a new driver.  This does TAINT the
 * kernel.  Calling this function indicates that the driver or subsystem has
 * had limited testing and is not marked for full support within this RHEL
 * minor release.  The next RHEL minor release may contain full support for
 * this driver.  Red Hat does not guarantee that bugs reported against this
 * driver or subsystem will be resolved.
 */
void mark_tech_preview(const char *msg, struct module *mod)
{
	const char *str = NULL;

	if (msg)
		str = msg;
#ifdef CONFIG_MODULES
	else if (mod && mod->name)
		str = mod->name;
#endif

	pr_warn("TECH PREVIEW: %s may not be fully supported.\n"
		"Please review provided documentation for limitations.\n",
		(str ? str : "kernel"));
	add_taint(TAINT_AUX, LOCKDEP_STILL_OK);
#ifdef CONFIG_MODULES
	if (mod)
		mod->taints |= (1U << TAINT_AUX);
#endif
}
EXPORT_SYMBOL(mark_tech_preview);

/**
 * mark_driver_unsupported - drivers that we know we don't want to support
 * @name: the name of the driver
 *
 * In some cases Red Hat has chosen to build a driver for internal QE
 * use. Use this function to mark those drivers as unsupported for
 * customers.
 */
void mark_driver_unsupported(const char *name)
{
	pr_crit("Warning: %s - This driver has not undergone sufficient testing by Red Hat for this release and therefore cannot be used in production systems.\n",
	        name ? name : "kernel");
}
EXPORT_SYMBOL(mark_driver_unsupported);

/**
 * mark_driver_deprecated() - Mark drivers as deprecated.
 * @name: the name of the driver
 *
 * Called to minimize the support status of a previously supported driver in
 * a minor release. This does not TAINT the kernel. Future
 * RHEL major releases may not include this driver. Driver updates and fixes
 * will be limited to critical issues in future minor releases.
 */
void mark_driver_deprecated(const char *name)
{
	pr_crit("Warning: %s - this driver is not recommended for new deployments. It continues to be supported in this RHEL release, but it is likely to be removed in the next major release. Driver updates and fixes will be limited to critical issues. Please contact Red Hat Support for additional information.\n",
	        name ? name : "kernel");
}
EXPORT_SYMBOL(mark_driver_deprecated);
