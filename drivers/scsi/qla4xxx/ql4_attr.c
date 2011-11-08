/*
 * QLogic iSCSI HBA Driver
 * Copyright (c)  2003-2011 QLogic Corporation
 *
 * See LICENSE.qla4xxx for copyright and licensing details.
 */

#include "ql4_def.h"
#include "ql4_glbl.h"
#include "ql4_dbg.h"

/* Scsi_Host attributes. */
static ssize_t
qla4xxx_fw_version_show(struct device *dev,
			struct device_attribute *attr, char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));

	if (is_qla8022(ha))
		return snprintf(buf, PAGE_SIZE, "%d.%02d.%02d (%x)\n",
				ha->firmware_version[0],
				ha->firmware_version[1],
				ha->patch_number, ha->build_number);
	else
		return snprintf(buf, PAGE_SIZE, "%d.%02d.%02d.%02d\n",
				ha->firmware_version[0],
				ha->firmware_version[1],
				ha->patch_number, ha->build_number);
}

static ssize_t
qla4xxx_serial_num_show(struct device *dev, struct device_attribute *attr,
			char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));
	return snprintf(buf, PAGE_SIZE, "%s\n", ha->serial_number);
}

static ssize_t
qla4xxx_iscsi_version_show(struct device *dev, struct device_attribute *attr,
			   char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));
	return snprintf(buf, PAGE_SIZE, "%d.%02d\n", ha->iscsi_major,
			ha->iscsi_minor);
}

static ssize_t
qla4xxx_optrom_version_show(struct device *dev, struct device_attribute *attr,
			    char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));
	return snprintf(buf, PAGE_SIZE, "%d.%02d.%02d.%02d\n",
			ha->bootload_major, ha->bootload_minor,
			ha->bootload_patch, ha->bootload_build);
}

static ssize_t
qla4xxx_board_id_show(struct device *dev, struct device_attribute *attr,
		      char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));
	return snprintf(buf, PAGE_SIZE, "0x%08X\n", ha->board_id);
}

static ssize_t
qla4xxx_fw_state_show(struct device *dev, struct device_attribute *attr,
		      char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));

	qla4xxx_get_firmware_state(ha);
	return snprintf(buf, PAGE_SIZE, "0x%08X%8X\n", ha->firmware_state,
			ha->addl_fw_state);
}

static ssize_t
qla4xxx_phy_port_cnt_show(struct device *dev, struct device_attribute *attr,
		      char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));

	if (!is_qla8022(ha))
		return -ENOSYS;

	return snprintf(buf, PAGE_SIZE, "0x%04X\n", ha->phy_port_cnt);
}

static ssize_t
qla4xxx_phy_port_num_show(struct device *dev, struct device_attribute *attr,
		      char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));

	if (!is_qla8022(ha))
		return -ENOSYS;

	return snprintf(buf, PAGE_SIZE, "0x%04X\n", ha->phy_port_num);
}

static ssize_t
qla4xxx_iscsi_func_cnt_show(struct device *dev, struct device_attribute *attr,
		      char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));

	if (!is_qla8022(ha))
		return -ENOSYS;

	return snprintf(buf, PAGE_SIZE, "0x%04X\n", ha->iscsi_pci_func_cnt);
}

static ssize_t
qla4xxx_hba_model_show(struct device *dev, struct device_attribute *attr,
		       char *buf)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));

	return snprintf(buf, PAGE_SIZE, "%s\n", ha->model_name);
}

static int qla4xxx_check_reset_type(char *str)
{
	if (strncmp(str, "adapter", 10) == 0)
		return QL4_SCSI_ADAPTER_RESET;
	else if (strncmp(str, "firmware", 10) == 0)
		return QL4_SCSI_FIRMWARE_RESET;
	else
		return 0;
}

static ssize_t
qla4xxx_store_host_reset(struct device *dev, struct device_attribute *attr,
			 const char *buf, size_t count)
{
	struct scsi_qla_host *ha = to_qla_host(class_to_shost(dev));
	int ret = -EINVAL;
	char str[10];
	int type;

	sscanf(buf, "%s", str);
	type = qla4xxx_check_reset_type(str);

	if (!type)
		goto exit_store_host_reset;

	ret = qla4xxx_host_reset(ha, type);

exit_store_host_reset:
	if (ret == 0)
		ret = count;
	return ret;
}

static DEVICE_ATTR(fw_version, S_IRUGO, qla4xxx_fw_version_show, NULL);
static DEVICE_ATTR(serial_num, S_IRUGO, qla4xxx_serial_num_show, NULL);
static DEVICE_ATTR(iscsi_version, S_IRUGO, qla4xxx_iscsi_version_show, NULL);
static DEVICE_ATTR(optrom_version, S_IRUGO, qla4xxx_optrom_version_show, NULL);
static DEVICE_ATTR(board_id, S_IRUGO, qla4xxx_board_id_show, NULL);
static DEVICE_ATTR(fw_state, S_IRUGO, qla4xxx_fw_state_show, NULL);
static DEVICE_ATTR(phy_port_cnt, S_IRUGO, qla4xxx_phy_port_cnt_show, NULL);
static DEVICE_ATTR(phy_port_num, S_IRUGO, qla4xxx_phy_port_num_show, NULL);
static DEVICE_ATTR(iscsi_func_cnt, S_IRUGO, qla4xxx_iscsi_func_cnt_show, NULL);
static DEVICE_ATTR(hba_model, S_IRUGO, qla4xxx_hba_model_show, NULL);
static DEVICE_ATTR(host_reset, S_IWUSR, NULL, qla4xxx_store_host_reset);

struct device_attribute *qla4xxx_host_attrs[] = {
	&dev_attr_fw_version,
	&dev_attr_serial_num,
	&dev_attr_iscsi_version,
	&dev_attr_optrom_version,
	&dev_attr_board_id,
	&dev_attr_fw_state,
	&dev_attr_phy_port_cnt,
	&dev_attr_phy_port_num,
	&dev_attr_iscsi_func_cnt,
	&dev_attr_hba_model,
	&dev_attr_host_reset,
	NULL,
};
