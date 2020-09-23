/*
 * Intel BayTrail PMIC I2C bus semaphore implementaion
 * Copyright (c) 2014, Intel Corporation.
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms and conditions of the GNU General Public License,
 * version 2, as published by the Free Software Foundation.
 *
 * This program is distributed in the hope it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
 * more details.
 */
#include <linux/device.h>
#include <linux/acpi.h>
#include <linux/i2c.h>
#include <linux/interrupt.h>

#include <asm/iosf_mbi.h>

#include "i2c-designware-core.h"

static int baytrail_i2c_acquire(struct dw_i2c_dev *dev)
{
	return iosf_mbi_block_punit_i2c_access();
}

static void baytrail_i2c_release(struct dw_i2c_dev *dev)
{
	iosf_mbi_unblock_punit_i2c_access();
}

int i2c_dw_probe_lock_support(struct dw_i2c_dev *dev)
{
	acpi_status status;
	unsigned long long shared_host = 0;
	acpi_handle handle;

	if (!dev || !dev->dev)
		return 0;

	handle = ACPI_HANDLE(dev->dev);
	if (!handle)
		return 0;

	status = acpi_evaluate_integer(handle, "_SEM", NULL, &shared_host);
	if (ACPI_FAILURE(status))
		return 0;

	if (!shared_host)
		return 0;

	if (!iosf_mbi_available())
		return -EPROBE_DEFER;

	dev_info(dev->dev, "I2C bus managed by PUNIT\n");
	dev->acquire_lock = baytrail_i2c_acquire;
	dev->release_lock = baytrail_i2c_release;
	dev->pm_disabled = true;

	return 0;
}

void i2c_dw_remove_lock_support(struct dw_i2c_dev *dev)
{
}
