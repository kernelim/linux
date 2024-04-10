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

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pci.h>
#include "rh_messages.h"

/**
 * mark_hardware_unmaintained() - Mark hardware as unmaintained.
 * @driver_name: driver name
 * @fmt: format for device description
 * @...: args for device description
 *
 * Called to notify users that the device will no longer be tested on a routine
 * basis and driver code associated with this device is no longer being updated.
 * Red Hat may, at their own discretion, fix security-related and critical
 * issues.  Support for this device will be disabled in a future major release
 * and users deploying this device should plan to replace the device in
 * production systems.
 *
 * This function should be used when the driver's usage can be tied to a
 * specific hardware device.  For example, a network device driver loading on a
 * specific device that is no longer maintained by the manufacturer.
 *
 * Reserved for Internal Red Hat use only.
 */
void __maybe_unused mark_hardware_unmaintained(const char *driver_name, char *fmt, ...)
{
	char device_description[DEV_DESC_LEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(device_description, DEV_DESC_LEN, fmt, args);
	pr_crit(RH_UNMAINT_HW, driver_name, device_description);
	va_end(args);
}
EXPORT_SYMBOL(mark_hardware_unmaintained);

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
 *
 * Reserved for Internal Red Hat use only.
 */
void __maybe_unused mark_hardware_deprecated(const char *driver_name, char *fmt, ...)
{
	char device_description[DEV_DESC_LEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(device_description, DEV_DESC_LEN, fmt, args);
	pr_crit(RH_DEPRECATED_HW, driver_name, device_description);
	va_end(args);
}

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
 *
 * Reserved for Internal Red Hat use only.
 */
static void __maybe_unused mark_hardware_disabled(const char *driver_name, char *fmt, ...)
{
	char device_description[DEV_DESC_LEN];
	va_list args;

	va_start(args, fmt);
	vsnprintf(device_description, DEV_DESC_LEN, fmt, args);
	pr_crit(RH_DISABLED_HW,	driver_name, device_description);
	va_end(args);
}

#ifdef CONFIG_PCI
/**
 * pci_hw_deprecated() - Mark a PCI device deprecated.
 * @dev: the PCI device structure to match against
 *
 * Called to check if this @dev is in the list of deprecated devices.
 *
 * Reserved for Internal Red Hat use only.
 */
static void __maybe_unused pci_hw_deprecated(struct pci_dev *dev)
{
	const struct pci_device_id *ret = pci_match_id(rh_deprecated_pci_devices, dev);

	if (!ret)
		return;

	mark_hardware_deprecated(dev_driver_string(&dev->dev), "%04X:%04X @ %s",
				 dev->vendor, dev->device, pci_name(dev));
}

/**
 * pci_hw_unmaintained() - Mark a PCI device unmaintained.
 * @dev: the PCI device structure to match against
 *
 * Called to check if this @dev is in the list of unmaintained devices.
 *
 * Reserved for Internal Red Hat use only.
 */
static void pci_hw_unmaintained(struct pci_dev *dev)
{
	const struct pci_device_id *ret = pci_match_id(rh_unmaintained_pci_devices, dev);

	if (!ret)
		return;

	mark_hardware_unmaintained(dev_driver_string(&dev->dev), "%04X:%04X @ %s",
				   dev->vendor, dev->device, pci_name(dev));
}

/**
 * pci_hw_disabled() - Mark a PCI device disabled.
 * @dev: the PCI device structure to match against
 *
 * Called to check if this @dev is in the list of disabled devices.
 *
 * Reserved for Internal Red Hat use only.
 */
static bool __maybe_unused pci_hw_disabled(struct pci_dev *dev)
{
	const struct pci_device_id *ret = pci_match_id(rh_disabled_pci_devices, dev);

	if (!ret)
		return false;

	mark_hardware_disabled(dev_driver_string(&dev->dev), "%04X:%04X @ %s",
			       dev->vendor, dev->device, pci_name(dev));
	return true;
}
#endif

/**
 * driver_unmaintained() - check to see if a driver is unmaintained
 * @module_name: module name
 *
 * Called to notify users that a driver will no longer be tested on a routine
 * basis and the driver code is no longer being updated.  Red Hat may fix
 * security-related and critical issues.  Support for this driver will be
 * disabled in a future major release, and users should replace any affected
 * devices in production systems.
 *
 * This function should be used when a driver's usage cannot be tied to a
 * specific hardware device.  For example, a network virtual interface driver
 * or a higher level storage layer driver that is no longer maintained
 * upstream.
 *
 * Reserved for Internal Red Hat use only.
 */
static void __maybe_unused driver_unmaintained(const char* module_name)
{
	int i = 0;

	while (rh_unmaintained_drivers[i]) {
		if (strcmp(rh_unmaintained_drivers[i], module_name) == 0) {
			pr_crit(RH_UNMAINT_DR, module_name);
			return;
		}
		i++;
	}
}

/**
 * driver_deprecated() - check to see if a driver is deprecated
 * @driver_name: module name
 *
 * Called to notify users that support for this driver is planned to be
 * unmaintained in a future major release, and will eventually be disabled in a
 * future major release.  This driver should not be used in new production
 * environments and users should replace any affected devices in production
 * systems.
 *
 * This function should be used when a driver's usage cannot be tied to a
 * specific hardware device.  For example, a network virtual interface driver
 * or a higher level storage layer driver that is no longer maintained
 * upstream.
 *
 * Reserved for Internal Red Hat use only.
 */
static void __maybe_unused driver_deprecated(const char* module_name)
{
	int i = 0;

	while (rh_deprecated_drivers[i]) {
		if (strcmp(rh_deprecated_drivers[i], module_name) == 0) {
			pr_crit(RH_DEPRECATED_DR, module_name);
			return;
		}
		i++;
	}
}

/* There is no driver_disabled() function.  Disabled drivers are configured off ;). */

/**
 * init_fn_unmaintained - check to see if a built-in driver is unmaintained.
 * @fn_name: module's module_init function name
 *
 * Called to notify users that a built-in driver will no longer be tested on a routine
 * basis and the built-in driver code is no longer being updated.  Red Hat may fix
 * security-related and critical issues.  Support for this built-in driver will be
 * disabled in a future major release, and users should replace any affected
 * devices in production systems.
 *
 * This function should be used when a built-in driver's usage cannot be tied
 * to a specific hardware device.  For example, a network virtual interface
 * driver or a higher level storage layer driver that is no longer maintained
 * upstream.
 *
 * Reserved for Internal Red Hat use only.
 */

static void __maybe_unused init_fn_unmaintained(char* fn_name)
{
	int i = 0;

	while (rh_unmaintained_init_fns[i]) {
		if (strcmp(rh_unmaintained_init_fns[i], fn_name) == 0) {
			pr_crit(RH_UNMAINT_DR, fn_name);
			return;
		}
		i++;
	}
}

/**
 * init_fn_deprecated() - check to see if a built-in driver is deprecated
 * @fn_name: module's module_init function name
 *
 * Called to notify users that support for this built-in driver is planned to be
 * unmaintained in a future major release, and will eventually be disabled in a
 * future major release.  This driver should not be used in new production
 * environments and users should replace any affected devices in production
 * systems.
 *
 * This function should be used when a built-in driver's usage cannot be tied
 * to a specific hardware device.  For example, a network virtual interface
 * driver or a higher level storage layer driver that is no longer maintained
 * upstream.
 *
 * Reserved for Internal Red Hat use only.
 */
static void __maybe_unused init_fn_deprecated(char* fn_name)
{
	int i = 0;

	while (rh_deprecated_init_fns[i]) {
		if (strcmp(rh_deprecated_init_fns[i], fn_name) == 0) {
			pr_crit(RH_DEPRECATED_DR, fn_name);
			return;
		}
		i++;
	}
}

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
 *
 * Reserved for Internal Red Hat use only.
 */
void __maybe_unused mark_tech_preview(const char *msg, struct module *mod)
{
	const char *str = NULL;

	if (msg)
		str = msg;
#ifdef CONFIG_MODULES
	else if (mod)
		str = mod->name;
#endif

	pr_warn(RH_TECH_PREVIEW, (str ? str : "kernel"));
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
 * kernel.  Calling this function indicates that the driver or subsystem
 * is not supported directly by Red Hat but by a partner engineer.
 *
 * Reserved for Internal Red Hat use only.
 */
void __maybe_unused mark_partner_supported(const char *msg, struct module *mod)
{
	const char *str = NULL;

	if (msg)
		str = msg;
#ifdef CONFIG_MODULES
	else if (mod)
		str = mod->name;
#endif

	pr_warn(RH_PARTNER_SUPPORTED, (str ? str : "kernel"));
	add_taint(TAINT_PARTNER_SUPPORTED, LOCKDEP_STILL_OK);
#ifdef CONFIG_MODULES
	if (mod)
		mod->taints |= (1U << TAINT_PARTNER_SUPPORTED);
#endif
}
EXPORT_SYMBOL(mark_partner_supported);

/*
 *
 * Functions called by 'main' kernel code.
 *
 */

#ifdef CONFIG_PCI
/**
 * pci_rh_check_status - checks the status of a PCI device.
 * @pci_dev: PCI device to be examined
 *
 * This function is called by the PCI driver subsystem to check the status of a
 * PCI device.
 *
 * This function returns true if the PCI device is disabled, and false otherwise.
 *
 * Reserved for Internal Red Hat use only.
 */
bool __maybe_unused pci_rh_check_status(struct pci_dev *pci_dev)
{
	if (pci_dev->driver->driver.owner != NULL) {
		if (!test_bit(TAINT_OOT_MODULE, &pci_dev->driver->driver.owner->taints)) {
			pci_hw_unmaintained(pci_dev);
			pci_hw_deprecated(pci_dev);
			return pci_hw_disabled(pci_dev);
		}
	}
	return false;
}
#endif

/** module_rh_check_status - checks the status of a module.
 * @module_name: Name of module to be examined
 *
 * This function is called by the module loading code to check the status of a
 * module.
 *
 * Reserved for Internal Red Hat use only.
 */
void __maybe_unused module_rh_check_status(const char * module_name)
{
	driver_unmaintained(module_name);
	driver_deprecated(module_name);
}

/**
  * init_rh_check_status - checks the status of a built-in module.
  * @fn_name: init function of module to be examined
  *
  * This function is called by the init code to check the status of a built-in module.
  * When a module is built-in, the module_init() function is converted into an initcall.
  * The initcall is the called during boot with the other system initcalls.
  *
  * Reserved for Internal Red Hat use only.
  */
void __maybe_unused init_rh_check_status(char *fn_name)
{
	init_fn_deprecated(fn_name);
	init_fn_unmaintained(fn_name);
}
