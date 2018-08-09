/*
 *  acpi_fan.c - ACPI Fan Driver ($Revision: 29 $)
 *
 *  Copyright (C) 2001, 2002 Andy Grover <andrew.grover@intel.com>
 *  Copyright (C) 2001, 2002 Paul Diefenbaugh <paul.s.diefenbaugh@intel.com>
 *
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or (at
 *  your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful, but
 *  WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *  General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License along
 *  with this program; if not, write to the Free Software Foundation, Inc.,
 *  59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.
 *
 * ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 */

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/types.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>
#include <linux/thermal.h>
#include <linux/nospec.h>
#include <acpi/acpi_bus.h>
#include <acpi/acpi_drivers.h>
#include <linux/sort.h>

#define ACPI_FAN_CLASS			"fan"
#define ACPI_FAN_FILE_STATE		"state"

#define _COMPONENT		ACPI_FAN_COMPONENT
ACPI_MODULE_NAME("fan");

MODULE_AUTHOR("Paul Diefenbaugh");
MODULE_DESCRIPTION("ACPI Fan Driver");
MODULE_LICENSE("GPL");

static int acpi_fan_add(struct acpi_device *device);
static int acpi_fan_remove(struct acpi_device *device, int type);

static const struct acpi_device_id fan_device_ids[] = {
	{"PNP0C0B", 0},
	{"INT3404", 0},
	{"", 0},
};
MODULE_DEVICE_TABLE(acpi, fan_device_ids);

struct acpi_fan_fps {
	u64 control;
	u64 trip_point;
	u64 speed;
	u64 noise_level;
	u64 power;
};

struct acpi_fan_fif {
	u64 revision;
	u64 fine_grain_ctrl;
	u64 step_size;
	u64 low_speed_notification;
};

struct acpi_fan {
	bool acpi4;
	struct acpi_fan_fif fif;
	struct acpi_fan_fps *fps;
	int fps_count;
	struct thermal_cooling_device *cdev;
};

static int acpi_fan_suspend(struct device *dev);
static int acpi_fan_resume(struct device *dev);
static struct dev_pm_ops acpi_fan_pm = {
	.resume = acpi_fan_resume,
	.freeze = acpi_fan_suspend,
	.thaw = acpi_fan_resume,
	.restore = acpi_fan_resume,
};
#define FAN_PM_OPS_PTR (&acpi_fan_pm)

static struct acpi_driver acpi_fan_driver = {
	.name = "fan",
	.class = ACPI_FAN_CLASS,
	.ids = fan_device_ids,
	.ops = {
		.add = acpi_fan_add,
		.remove = acpi_fan_remove,
		},
	.drv.pm = FAN_PM_OPS_PTR,
};

/* thermal cooling device callbacks */
static int fan_get_max_state(struct thermal_cooling_device *cdev, unsigned long
			     *state)
{
	struct acpi_device *device = cdev->devdata;
	struct acpi_fan *fan = acpi_driver_data(device);

	if (fan->acpi4)
		*state = fan->fps_count - 1;
	else
		*state = 1;
	return 0;
}

static int fan_get_state_acpi4(struct acpi_device *device, unsigned long *state)
{
	struct acpi_buffer buffer = { ACPI_ALLOCATE_BUFFER, NULL };
	struct acpi_fan *fan = acpi_driver_data(device);
	union acpi_object *obj;
	acpi_status status;
	int control, i;

	status = acpi_evaluate_object(device->handle, "_FST", NULL, &buffer);
	if (ACPI_FAILURE(status)) {
		dev_err(&device->dev, "Get fan state failed\n");
		return status;
	}

	obj = buffer.pointer;
	if (!obj || obj->type != ACPI_TYPE_PACKAGE ||
	    obj->package.count != 3 ||
	    obj->package.elements[1].type != ACPI_TYPE_INTEGER) {
		dev_err(&device->dev, "Invalid _FST data\n");
		status = -EINVAL;
		goto err;
	}

	control = obj->package.elements[1].integer.value;
	for (i = 0; i < fan->fps_count; i++) {
		if (control == fan->fps[i].control)
			break;
	}
	if (i == fan->fps_count) {
		dev_dbg(&device->dev, "Invalid control value returned\n");
		status = -EINVAL;
		goto err;
	}

	*state = i;

err:
	kfree(obj);
	return status;
}

static int fan_get_state(struct acpi_device *device, unsigned long *state)
{
	int result;
	int acpi_state = ACPI_STATE_D0;

	result = acpi_bus_get_power(device->handle, &acpi_state);
	if (result)
		return result;

	*state = (acpi_state == ACPI_STATE_D3 ? 0 :
		 (acpi_state == ACPI_STATE_D0 ? 1 : -1));
	return 0;
}

static int fan_get_cur_state(struct thermal_cooling_device *cdev, unsigned long
			     *state)
{
	struct acpi_device *device = cdev->devdata;
	struct acpi_fan *fan = acpi_driver_data(device);

	if (fan->acpi4)
		return fan_get_state_acpi4(device, state);
	else
		return fan_get_state(device, state);
}

static int fan_set_state(struct acpi_device *device, unsigned long state)
{
	int ret;

	if (state != 0 && state != 1)
		return -EINVAL;

	device->flags.force_power_state = 1;
	ret = acpi_bus_set_power(device->handle,
				     state ? ACPI_STATE_D0 : ACPI_STATE_D3);
	device->flags.force_power_state = 0;

	return ret;
}

static int fan_set_state_acpi4(struct acpi_device *device, unsigned long state)
{
	struct acpi_fan *fan = acpi_driver_data(device);
	acpi_status status;
	union acpi_object arg0 = { ACPI_TYPE_INTEGER };
	struct acpi_object_list args = { 1, &arg0 };

	if (state >= fan->fps_count)
		return -EINVAL;
	state = array_index_nospec(state, fan->fps_count);

	arg0.integer.value = fan->fps[state].control;

	status = acpi_evaluate_object(device->handle, "_FSL", &args, NULL);
	if (ACPI_FAILURE(status)) {
		dev_dbg(&device->dev, "Failed to set state by _FSL\n");
		return status;
	}

	return 0;
}

static int
fan_set_cur_state(struct thermal_cooling_device *cdev, unsigned long state)
{
	struct acpi_device *device = cdev->devdata;
	struct acpi_fan *fan = acpi_driver_data(device);

	if (fan->acpi4)
		return fan_set_state_acpi4(device, state);
	else
		return fan_set_state(device, state);
}

static struct thermal_cooling_device_ops fan_cooling_ops = {
	.get_max_state = fan_get_max_state,
	.get_cur_state = fan_get_cur_state,
	.set_cur_state = fan_set_cur_state,
};

/* --------------------------------------------------------------------------
                              FS Interface (/proc)
   -------------------------------------------------------------------------- */
#ifdef CONFIG_ACPI_PROCFS

static struct proc_dir_entry *acpi_fan_dir;

static int acpi_fan_read_state(struct seq_file *seq, void *offset)
{
	struct acpi_device *device = seq->private;
	int state = 0;


	if (device) {
		if (acpi_bus_get_power(device->handle, &state))
			seq_printf(seq, "status:                  ERROR\n");
		else
			seq_printf(seq, "status:                  %s\n",
				   !state ? "on" : "off");
	}
	return 0;
}

static int acpi_fan_state_open_fs(struct inode *inode, struct file *file)
{
	return single_open(file, acpi_fan_read_state, PDE(inode)->data);
}

static ssize_t
acpi_fan_write_state(struct file *file, const char __user * buffer,
		     size_t count, loff_t * ppos)
{
	int result = 0;
	struct seq_file *m = file->private_data;
	struct acpi_device *device = m->private;
	char state_string[3] = { '\0' };

	if (count > sizeof(state_string) - 1)
		return -EINVAL;

	if (copy_from_user(state_string, buffer, count))
		return -EFAULT;

	state_string[count] = '\0';
	if ((state_string[0] < '0') || (state_string[0] > '3'))
		return -EINVAL;
	if (state_string[1] == '\n')
		state_string[1] = '\0';
	if (state_string[1] != '\0')
		return -EINVAL;

	result = acpi_bus_set_power(device->handle,
				    simple_strtoul(state_string, NULL, 0));
	if (result)
		return result;

	return count;
}

static const struct file_operations acpi_fan_state_ops = {
	.open = acpi_fan_state_open_fs,
	.read = seq_read,
	.write = acpi_fan_write_state,
	.llseek = seq_lseek,
	.release = single_release,
	.owner = THIS_MODULE,
};

static int acpi_fan_add_fs(struct acpi_device *device)
{
	struct proc_dir_entry *entry = NULL;


	if (!device)
		return -EINVAL;

	if (!acpi_device_dir(device)) {
		acpi_device_dir(device) = proc_mkdir(acpi_device_bid(device),
						     acpi_fan_dir);
		if (!acpi_device_dir(device))
			return -ENODEV;
	}

	/* 'status' [R/W] */
	entry = proc_create_data(ACPI_FAN_FILE_STATE,
				 S_IFREG | S_IRUGO | S_IWUSR,
				 acpi_device_dir(device),
				 &acpi_fan_state_ops,
				 device);
	if (!entry)
		return -ENODEV;
	return 0;
}

static int acpi_fan_remove_fs(struct acpi_device *device)
{

	if (acpi_device_dir(device)) {
		remove_proc_entry(ACPI_FAN_FILE_STATE, acpi_device_dir(device));
		remove_proc_entry(acpi_device_bid(device), acpi_fan_dir);
		acpi_device_dir(device) = NULL;
	}

	return 0;
}
#else
static int acpi_fan_add_fs(struct acpi_device *device)
{
	return 0;
}

static int acpi_fan_remove_fs(struct acpi_device *device)
{
	return 0;
}
#endif
/* --------------------------------------------------------------------------
 *                               Driver Interface
 * --------------------------------------------------------------------------
*/

static bool acpi_fan_is_acpi4(struct acpi_device *device)
{
	acpi_handle tmp;

	return ACPI_SUCCESS(acpi_get_handle(device->handle, "_FIF", &tmp)) &&
	       ACPI_SUCCESS(acpi_get_handle(device->handle, "_FPS", &tmp)) &&
	       ACPI_SUCCESS(acpi_get_handle(device->handle, "_FSL", &tmp)) &&
	       ACPI_SUCCESS(acpi_get_handle(device->handle, "_FST", &tmp));
}

static int acpi_fan_get_fif(struct acpi_device *device)
{
	struct acpi_buffer buffer = { ACPI_ALLOCATE_BUFFER, NULL };
	struct acpi_fan *fan = acpi_driver_data(device);
	struct acpi_buffer format = { sizeof("NNNN"), "NNNN" };
	struct acpi_buffer fif = { sizeof(fan->fif), &fan->fif };
	union acpi_object *obj;
	acpi_status status;

	status = acpi_evaluate_object(device->handle, "_FIF", NULL, &buffer);
	if (ACPI_FAILURE(status))
		return status;

	obj = buffer.pointer;
	if (!obj || obj->type != ACPI_TYPE_PACKAGE) {
		dev_err(&device->dev, "Invalid _FIF data\n");
		status = -EINVAL;
		goto err;
	}

	status = acpi_extract_package(obj, &format, &fif);
	if (ACPI_FAILURE(status)) {
		dev_err(&device->dev, "Invalid _FIF element\n");
		status = -EINVAL;
	}

err:
	kfree(obj);
	return status;
}

static int acpi_fan_speed_cmp(const void *a, const void *b)
{
	const struct acpi_fan_fps *fps1 = a;
	const struct acpi_fan_fps *fps2 = b;
	return fps1->speed - fps2->speed;
}

static int acpi_fan_get_fps(struct acpi_device *device)
{
	struct acpi_fan *fan = acpi_driver_data(device);
	struct acpi_buffer buffer = { ACPI_ALLOCATE_BUFFER, NULL };
	union acpi_object *obj;
	acpi_status status;
	int i;

	status = acpi_evaluate_object(device->handle, "_FPS", NULL, &buffer);
	if (ACPI_FAILURE(status))
		return status;

	obj = buffer.pointer;
	if (!obj || obj->type != ACPI_TYPE_PACKAGE || obj->package.count < 2) {
		dev_err(&device->dev, "Invalid _FPS data\n");
		status = -EINVAL;
		goto err;
	}

	fan->fps_count = obj->package.count - 1; /* minus revision field */
	fan->fps = devm_kzalloc(&device->dev,
				fan->fps_count * sizeof(struct acpi_fan_fps),
				GFP_KERNEL);
	if (!fan->fps) {
		dev_err(&device->dev, "Not enough memory\n");
		status = -ENOMEM;
		goto err;
	}
	for (i = 0; i < fan->fps_count; i++) {
		struct acpi_buffer format = { sizeof("NNNNN"), "NNNNN" };
		struct acpi_buffer fps = { sizeof(fan->fps[i]), &fan->fps[i] };
		status = acpi_extract_package(&obj->package.elements[i + 1],
					      &format, &fps);
		if (ACPI_FAILURE(status)) {
			dev_err(&device->dev, "Invalid _FPS element\n");
			break;
		}
	}

	/* sort the state array according to fan speed in increase order */
	sort(fan->fps, fan->fps_count, sizeof(*fan->fps),
	     acpi_fan_speed_cmp, NULL);

err:
	kfree(obj);
	return status;
}

static int acpi_fan_add(struct acpi_device *device)
{
	int result = 0;
	int state = 0;
	struct acpi_fan *fan;
	struct thermal_cooling_device *cdev;
	char *name;

	strcpy(acpi_device_name(device), "Fan");
	strcpy(acpi_device_class(device), ACPI_FAN_CLASS);

	fan = kzalloc(sizeof(*fan), GFP_KERNEL);
	if (!fan) {
		dev_err(&device->dev, "No memory for fan\n");
		return -ENOMEM;
	}
	device->driver_data = fan;

	if (acpi_fan_is_acpi4(device)) {
		if (acpi_fan_get_fif(device) || acpi_fan_get_fps(device))
			goto end;
		fan->acpi4 = true;
	} else {
	result = acpi_bus_get_power(device->handle, &state);
		if (result) {
			dev_err(&device->dev, "Setting initial power state\n");
			goto end;
		}
	}

	device->flags.force_power_state = 1;
	acpi_bus_set_power(device->handle, state);
	device->flags.force_power_state = 0;

	if (!strncmp(acpi_device_hid(device), "PNP0C0B", strlen("PNP0C0B")))
		name = "Fan";
	else
		name = acpi_device_bid(device);

	cdev = thermal_cooling_device_register(name, device,
						&fan_cooling_ops);
	if (IS_ERR(cdev)) {
		result = PTR_ERR(cdev);
		goto end;
	}

	dev_dbg(&device->dev, "registered as cooling_device%d\n", cdev->id);

	device->driver_data = cdev;
	fan->cdev = cdev;
	result = sysfs_create_link(&device->dev.kobj,
				   &cdev->device.kobj,
				   "thermal_cooling");
	if (result)
		dev_err(&device->dev, "Failed to create sysfs link "
			"'thermal_cooling'\n");

	result = sysfs_create_link(&cdev->device.kobj,
				   &device->dev.kobj,
				   "device");
	if (result)
		dev_err(&device->dev, "Failed to create sysfs link 'device'\n");

	result = acpi_fan_add_fs(device);
	if (result)
		goto end;

end:
	return result;
}

static int acpi_fan_remove(struct acpi_device *device, int type)
{
	struct acpi_fan *fan = acpi_driver_data(device);

	acpi_fan_remove_fs(device);
	sysfs_remove_link(&device->dev.kobj, "thermal_cooling");
	sysfs_remove_link(&fan->cdev->device.kobj, "device");
	thermal_cooling_device_unregister(fan->cdev);

	return 0;
}

static int acpi_fan_suspend(struct device *dev)
{
	struct acpi_device *adev = to_acpi_device(dev);
	struct acpi_fan *fan = acpi_driver_data(adev);
	if (fan->acpi4)
		return 0;

	adev->flags.force_power_state = 1;
	acpi_bus_set_power(adev->handle, ACPI_STATE_D0);
	adev->flags.force_power_state = 0;

	return AE_OK;
}

static int acpi_fan_resume(struct device *dev)
{
	int result = 0;
	int power_state = 0;
	struct acpi_fan *fan = dev_get_drvdata(dev);

	if (fan->acpi4)
		return 0;

	result = acpi_bus_get_power(to_acpi_device(dev)->handle, NULL);
	if (result) {
		dev_err(dev, "Error updating fan power state\n");
		return result;
	}

	to_acpi_device(dev)->flags.force_power_state = 1;
	acpi_bus_set_power(to_acpi_device(dev)->handle, power_state);
	to_acpi_device(dev)->flags.force_power_state = 0;

	return result;
}

static int __init acpi_fan_init(void)
{
	int result = 0;

#ifdef CONFIG_ACPI_PROCFS
	acpi_fan_dir = proc_mkdir(ACPI_FAN_CLASS, acpi_root_dir);
	if (!acpi_fan_dir)
		return -ENODEV;
#endif

	result = acpi_bus_register_driver(&acpi_fan_driver);
	if (result < 0) {
#ifdef CONFIG_ACPI_PROCFS
		remove_proc_entry(ACPI_FAN_CLASS, acpi_root_dir);
#endif
		return -ENODEV;
	}

	return 0;
}

static void __exit acpi_fan_exit(void)
{

	acpi_bus_unregister_driver(&acpi_fan_driver);

#ifdef CONFIG_ACPI_PROCFS
	remove_proc_entry(ACPI_FAN_CLASS, acpi_root_dir);
#endif

	return;
}

module_init(acpi_fan_init);
module_exit(acpi_fan_exit);
