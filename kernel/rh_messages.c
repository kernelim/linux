#include <linux/kernel.h>
#include <linux/module.h>

#define DEV_DESC_LEN 256
/*
 * The following functions are used by Red Hat to indicate to users that
 * hardware and drivers are unsupported, or have limited support in RHEL major
 * and minor releases.  These functions output loud warning messages to the end
 * user and should be USED WITH CAUTION.
 *
 * Any use of these functions _MUST_ be documented in the RHEL Release Notes,
 * and have approval of management.
 *
 * Generally, the process of disabling a driver or device in RHEL requires the
 * driver or device to be marked as 'deprecated' in all existing releases, and
 * then either 'unmaintained' or 'disabled' in a future release.
 *
 * In general, deprecated and unmaintained drivers continue to receive security
 * related fixes until they are disabled.
 */

/**
 * mark_hardware_unmaintained() - Mark hardware as unmaintained.
 * @driver_name: driver name
 * @fmt: format for device description
 * @...: args for device description
 *
 * Called to notify users that the device will no longer be tested on a routine
 * basis and driver code associated with this device is no longer being updated.
 * Red Hat may fix security-related and critical issues.  Support for this device
 * will be disabled in a future major release and users deploying this device
 * should plan to replace the device in production systems.
 *
 * This function should be used when the driver's usage can be tied to a
 * specific hardware device.  For example, a network device driver loading on a
 * specific device that is no longer maintained by the manufacturer.
 */
void mark_hardware_unmaintained(const char *driver_name, char *fmt, ...)
{
	char device_description[DEV_DESC_LEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(device_description, DEV_DESC_LEN, fmt, args);
	pr_crit("Warning: Unmaintained hardware is detected:  %s:%s\n", driver_name,
		device_description);
	va_end(args);
}
EXPORT_SYMBOL(mark_hardware_unmaintained);

/**
 * mark_driver_unmaintained() - Mark a driver as unmaintained.
 * @driver_name: driver name
 *
 * Called to notify users that a driver will no longer be tested on a routine
 * basis and the driver code is no longer being updated.  Red Hat may fix
 * security-related and critical issues.  Support for this driver will be
 * disabled in a future major release, and users should replace any affected
 * devices in production systems.
 *
 * This function should be used when a driver's usage cannot be tied to a
 * specific hardware device.  For example, a network bonding driver or a higher
 * level storage layer driver that is no longer maintained upstream.
 */
void mark_driver_unmaintained(const char *driver_name)
{
	pr_crit("Warning: Unmaintained driver is detected:  %s\n", driver_name);
}
EXPORT_SYMBOL(mark_driver_unmaintained);

/**
 * mark_hardware_deprecated() - Mark hardware as deprecated.
 * @driver_name: driver name
 * @fmt: format for device description
 * @...: args for device description
 *
 * Called to notify users that support for the device is planned to be
 * unmaintained in a future major release, and will eventually be disabled in a
 * future major release.  This device should not be used in new production
 * environments and users should replace the device in production systems.
 *
 * This function should be used when the driver's usage can be tied to a
 * specific hardware device.  For example, a network device driver loading on a
 * specific device that is no longer maintained by the manufacturer.
 */
void mark_hardware_deprecated(const char *driver_name, char *fmt, ...)
{
	char device_description[DEV_DESC_LEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(device_description, DEV_DESC_LEN, fmt, args);
	pr_crit("Warning: Deprecated Hardware is detected: %s:%s will not be maintained in a future major release and may be disabled\n",
		driver_name, device_description);
	va_end(args);
}
EXPORT_SYMBOL(mark_hardware_deprecated);

/**
 * mark_driver_deprecated() - Mark a driver as deprecated.
 * @driver_name: driver name
 *
 * Called to notify users that support for this driver is planned to be
 * unmaintained in a future major release, and will eventually be disabled in a
 * future major release.  This driver should not be used in new production
 * environments and users should replace any affected devices in production
 * systems.
 *
 * This function should be used when a driver's usage cannot be tied to a
 * specific hardware device.  For example, a network bonding driver or a higher
 * level storage layer driver that is no longer maintained upstream.
 */
void mark_driver_deprecated(const char *driver_name)
{
	pr_crit("Warning: Deprecated Driver is detected: %s will not be maintained in a future major release and may be disabled\n",
		driver_name);
}
EXPORT_SYMBOL(mark_driver_deprecated);

/**
 * mark_hardware_disabled() - Mark a driver as removed.
 * @driver_name: driver name
 * @fmt: format for device description
 * @...: args for device description
 *
 * Called to notify users that a device's support has been completely disabled
 * and no future support updates will occur.  This device cannot be used in new
 * production environments, and users must replace the device in production
 * systems.
 *
 * This function should be used when the driver's usage can be tied to a
 * specific hardware device.  For example, a network device driver loading on a
 * specific device that is no longer maintained by the manufacturer.
 */
void mark_hardware_disabled(const char *driver_name, char *fmt, ...)
{
	char device_description[DEV_DESC_LEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(device_description, DEV_DESC_LEN, fmt, args);
	pr_crit("Warning: Disabled Hardware is detected: %s:%s is no longer enabled in this release.\n",
		driver_name, device_description);
	va_end(args);
}
EXPORT_SYMBOL(mark_hardware_disabled);

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
	else if (mod)
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
 * mark_partner_supported() - Mark driver or kernel subsystem as 'Partner Supported'
 * @msg: Driver or kernel subsystem name
 *
 * Called to minimize the support status of a new driver.  This does TAINT the
 * kernel.  Calling this function indicates that the driver or subsystem has
 * is not supported directly by Red Hat but by a partner engineer.
 */
void mark_partner_supported(const char *msg, struct module *mod)
{
	const char *str = NULL;

	if (msg)
		str = msg;
#ifdef CONFIG_MODULES
	else if (mod)
		str = mod->name;
#endif

	pr_warn("Warning: %s is a Partner supported GPL module and not supported directly by Red Hat.\n",
		(str ? str : "kernel"));
	add_taint(TAINT_PARTNER_SUPPORTED, LOCKDEP_STILL_OK);
#ifdef CONFIG_MODULES
	if (mod)
		mod->taints |= (1U << TAINT_PARTNER_SUPPORTED);
#endif
}
EXPORT_SYMBOL(mark_partner_supported);
