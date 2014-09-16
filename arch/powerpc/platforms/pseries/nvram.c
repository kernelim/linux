/*
 *  c 2001 PPC 64 Team, IBM Corp
 *
 *      This program is free software; you can redistribute it and/or
 *      modify it under the terms of the GNU General Public License
 *      as published by the Free Software Foundation; either version
 *      2 of the License, or (at your option) any later version.
 *
 * /dev/nvram driver for PPC64
 *
 * This perhaps should live in drivers/char
 */


#include <linux/types.h>
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/kmsg_dump.h>
#include <linux/pstore.h>
#include <linux/ctype.h>
#include <asm/uaccess.h>
#include <asm/nvram.h>
#include <asm/rtas.h>
#include <asm/prom.h>
#include <asm/machdep.h>

/*
 * Set oops header version to distingush between old and new format header.
 * lnx,oops-log partition max size is 4000, header version > 4000 will
 * help in identifying new header.
 */
#define OOPS_HDR_VERSION 5000

static unsigned int nvram_size;
static int nvram_fetch, nvram_store;
static char nvram_buf[NVRW_CNT];	/* assume this is in the first 4GB */
static DEFINE_SPINLOCK(nvram_lock);

struct err_log_info {
	int error_type;
	unsigned int seq_num;
};

struct nvram_os_partition {
	const char *name;
	int req_size;	/* desired size, in bytes */
	int min_size;	/* minimum acceptable size (0 means req_size) */
	long size;	/* size of data portion (excluding err_log_info) */
	long index;	/* offset of data portion of partition */
	bool os_partition; /* partition initialized by OS, not FW */
};

static struct nvram_os_partition rtas_log_partition = {
	.name = "ibm,rtas-log",
	.req_size = 2079,
	.min_size = 1055,
	.index = -1,
	.os_partition = true
};

static struct nvram_os_partition oops_log_partition = {
	.name = "lnx,oops-log",
	.req_size = 4000,
	.min_size = 2000,
	.index = -1,
	.os_partition = true
};

static const char *const pseries_nvram_os_partitions[] = {
	"ibm,rtas-log",
	"lnx,oops-log",
	NULL
};

struct oops_log_info {
	u16 version;
	u16 report_length;
	u64 timestamp;
} __attribute__((packed));

static void oops_to_nvram(struct kmsg_dumper *dumper,
		enum kmsg_dump_reason reason,
		const char *old_msgs, unsigned long old_len,
		const char *new_msgs, unsigned long new_len);

static struct kmsg_dumper nvram_kmsg_dumper = {
	.dump = oops_to_nvram
};

/* See clobbering_unread_rtas_event() */
#define NVRAM_RTAS_READ_TIMEOUT 5		/* seconds */
static unsigned long last_unread_rtas_event;	/* timestamp */

/* We preallocate oops_buf during init to avoid kmalloc during oops/panic. */
static char *oops_data;
static size_t oops_data_sz;
static char *oops_buf;

#ifdef CONFIG_PSTORE
static struct nvram_os_partition of_config_partition = {
	.name = "of-config",
	.index = -1,
	.os_partition = false
};

static struct nvram_os_partition common_partition = {
	.name = "common",
	.index = -1,
	.os_partition = false
};

static enum pstore_type_id nvram_type_ids[] = {
	PSTORE_TYPE_DMESG,
	PSTORE_TYPE_PPC_RTAS,
	PSTORE_TYPE_PPC_OF,
	PSTORE_TYPE_PPC_COMMON,
	-1
};
static int read_type;
static unsigned long last_rtas_event;
#endif

static ssize_t pSeries_nvram_read(char *buf, size_t count, loff_t *index)
{
	unsigned int i;
	unsigned long len;
	int done;
	unsigned long flags;
	char *p = buf;


	if (nvram_size == 0 || nvram_fetch == RTAS_UNKNOWN_SERVICE)
		return -ENODEV;

	if (*index >= nvram_size)
		return 0;

	i = *index;
	if (i + count > nvram_size)
		count = nvram_size - i;

	spin_lock_irqsave(&nvram_lock, flags);

	for (; count != 0; count -= len) {
		len = count;
		if (len > NVRW_CNT)
			len = NVRW_CNT;
		
		if ((rtas_call(nvram_fetch, 3, 2, &done, i, __pa(nvram_buf),
			       len) != 0) || len != done) {
			spin_unlock_irqrestore(&nvram_lock, flags);
			return -EIO;
		}
		
		memcpy(p, nvram_buf, len);

		p += len;
		i += len;
	}

	spin_unlock_irqrestore(&nvram_lock, flags);
	
	*index = i;
	return p - buf;
}

static ssize_t pSeries_nvram_write(char *buf, size_t count, loff_t *index)
{
	unsigned int i;
	unsigned long len;
	int done;
	unsigned long flags;
	const char *p = buf;

	if (nvram_size == 0 || nvram_store == RTAS_UNKNOWN_SERVICE)
		return -ENODEV;

	if (*index >= nvram_size)
		return 0;

	i = *index;
	if (i + count > nvram_size)
		count = nvram_size - i;

	spin_lock_irqsave(&nvram_lock, flags);

	for (; count != 0; count -= len) {
		len = count;
		if (len > NVRW_CNT)
			len = NVRW_CNT;

		memcpy(nvram_buf, p, len);

		if ((rtas_call(nvram_store, 3, 2, &done, i, __pa(nvram_buf),
			       len) != 0) || len != done) {
			spin_unlock_irqrestore(&nvram_lock, flags);
			return -EIO;
		}
		
		p += len;
		i += len;
	}
	spin_unlock_irqrestore(&nvram_lock, flags);
	
	*index = i;
	return p - buf;
}

static ssize_t pSeries_nvram_get_size(void)
{
	return nvram_size ? nvram_size : -ENODEV;
}


/* nvram_write_os_partition, nvram_write_error_log
 *
 * We need to buffer the error logs into nvram to ensure that we have
 * the failure information to decode.  If we have a severe error there
 * is no way to guarantee that the OS or the machine is in a state to
 * get back to user land and write the error to disk.  For example if
 * the SCSI device driver causes a Machine Check by writing to a bad
 * IO address, there is no way of guaranteeing that the device driver
 * is in any state that is would also be able to write the error data
 * captured to disk, thus we buffer it in NVRAM for analysis on the
 * next boot.
 *
 * In NVRAM the partition containing the error log buffer will looks like:
 * Header (in bytes):
 * +-----------+----------+--------+------------+------------------+
 * | signature | checksum | length | name       | data             |
 * |0          |1         |2      3|4         15|16        length-1|
 * +-----------+----------+--------+------------+------------------+
 *
 * The 'data' section would look like (in bytes):
 * +--------------+------------+-----------------------------------+
 * | event_logged | sequence # | error log                         |
 * |0            3|4          7|8                  error_log_size-1|
 * +--------------+------------+-----------------------------------+
 *
 * event_logged: 0 if event has not been logged to syslog, 1 if it has
 * sequence #: The unique sequence # for each event. (until it wraps)
 * error log: The error log from event_scan
 */
int nvram_write_os_partition(struct nvram_os_partition *part, char * buff,
		int length, unsigned int err_type, unsigned int error_log_cnt)
{
	int rc;
	loff_t tmp_index;
	struct err_log_info info;
	
	if (part->index < 0) {
		return -ESPIPE;
	}

	if (length > part->size) {
		length = part->size;
	}

	info.error_type = err_type;
	info.seq_num = error_log_cnt;

	tmp_index = part->index;

	rc = ppc_md.nvram_write((char *)&info, sizeof(struct err_log_info), &tmp_index);
	if (rc <= 0) {
		pr_err("%s: Failed nvram_write (%d)\n", __FUNCTION__, rc);
		return rc;
	}

	rc = ppc_md.nvram_write(buff, length, &tmp_index);
	if (rc <= 0) {
		pr_err("%s: Failed nvram_write (%d)\n", __FUNCTION__, rc);
		return rc;
	}
	
	return 0;
}

int nvram_write_error_log(char * buff, int length,
                          unsigned int err_type, unsigned int error_log_cnt)
{
	int rc = nvram_write_os_partition(&rtas_log_partition, buff, length,
						err_type, error_log_cnt);
	if (!rc) {
		last_unread_rtas_event = get_seconds();
#ifdef CONFIG_PSTORE
		last_rtas_event = get_seconds();
#endif
	}

	return rc;
}

/* nvram_read_partition
 *
 * Reads nvram partition for at most 'length'
 */
int nvram_read_partition(struct nvram_os_partition *part, char *buff,
			int length, unsigned int *err_type,
			unsigned int *error_log_cnt)
{
	int rc;
	loff_t tmp_index;
	struct err_log_info info;
	
	if (part->index == -1)
		return -1;

	if (length > part->size)
		length = part->size;

	tmp_index = part->index;

	if (part->os_partition) {
		rc = ppc_md.nvram_read((char *)&info,
					sizeof(struct err_log_info),
					&tmp_index);
		if (rc <= 0) {
			pr_err("%s: Failed nvram_read (%d)\n", __FUNCTION__,
									rc);
			return rc;
		}
	}

	rc = ppc_md.nvram_read(buff, length, &tmp_index);
	if (rc <= 0) {
		pr_err("%s: Failed nvram_read (%d)\n", __FUNCTION__, rc);
		return rc;
	}

	if (part->os_partition) {
		*error_log_cnt = info.seq_num;
		*err_type = info.error_type;
	}

	return 0;
}

/* nvram_read_error_log
 *
 * Reads nvram for error log for at most 'length'
 */
int nvram_read_error_log(char *buff, int length,
			unsigned int *err_type, unsigned int *error_log_cnt)
{
	return nvram_read_partition(&rtas_log_partition, buff, length,
						err_type, error_log_cnt);
}


/* This doesn't actually zero anything, but it sets the event_logged
 * word to tell that this event is safely in syslog.
 */
int nvram_clear_error_log(void)
{
	loff_t tmp_index;
	int clear_word = ERR_FLAG_ALREADY_LOGGED;
	int rc;

	if (rtas_log_partition.index < 0)
		return -1;

	tmp_index = rtas_log_partition.index;
	
	rc = ppc_md.nvram_write((char *)&clear_word, sizeof(int), &tmp_index);
	if (rc <= 0) {
		printk(KERN_ERR "nvram_clear_error_log: Failed nvram_write (%d)\n", rc);
		return rc;
	}
	last_unread_rtas_event = 0;

	return 0;
}

/* pseries_nvram_init_os_partition
 *
 * This sets up a partition with an "OS" signature.
 *
 * The general strategy is the following:
 * 1.) If a partition with the indicated name already exists...
 *	- If it's large enough, use it.
 *	- Otherwise, recycle it and keep going.
 * 2.) Search for a free partition that is large enough.
 * 3.) If there's not a free partition large enough, recycle any obsolete
 * OS partitions and try again.
 * 4.) Will first try getting a chunk that will satisfy the requested size.
 * 5.) If a chunk of the requested size cannot be allocated, then try finding
 * a chunk that will satisfy the minimum needed.
 *
 * Returns 0 on success, else -1.
 */
static int __init pseries_nvram_init_os_partition(struct nvram_os_partition
									*part)
{
	loff_t p;
	int size;

	/* Scan nvram for partitions */
	nvram_scan_partitions();

	/* Look for ours */
	p = nvram_find_partition2(part->name, NVRAM_SIG_OS, &size);

	/* Found one but too small, remove it */
	if (p && size < part->min_size) {
		pr_info("nvram: Found too small %s partition,"
					" removing it...\n", part->name);
		nvram_remove_partition(part->name, NVRAM_SIG_OS, NULL);
		p = 0;
	}

	/* Create one if we didn't find */
	if (!p) {
		p = nvram_create_partition(part->name, NVRAM_SIG_OS,
					part->req_size, part->min_size);
		if (p == -ENOSPC) {
			pr_info("nvram: No room to create %s partition, "
				"deleting any obsolete OS partitions...\n",
				part->name);
			nvram_remove_partition(NULL, NVRAM_SIG_OS,
						pseries_nvram_os_partitions);
			p = nvram_create_partition(part->name, NVRAM_SIG_OS,
					part->req_size, part->min_size);
		}
	}

	if (p <= 0) {
		pr_err("nvram: Failed to find or create %s"
		       " partition, err %d\n", part->name, (int)p);
		return -1;
	}

	part->index = p;
	part->size = nvram_get_partition_size(p) - sizeof(struct err_log_info);
	
	return 0;
}

/*
 * Are we using the ibm,rtas-log for oops/panic reports?  And if so,
 * would logging this oops/panic overwrite an RTAS event that rtas_errd
 * hasn't had a chance to read and process?  Return 1 if so, else 0.
 *
 * We assume that if rtas_errd hasn't read the RTAS event in
 * NVRAM_RTAS_READ_TIMEOUT seconds, it's probably not going to.
 */
static int clobbering_unread_rtas_event(void)
{
	return (oops_log_partition.index == rtas_log_partition.index
		&& last_unread_rtas_event
		&& get_seconds() - last_unread_rtas_event <=
						NVRAM_RTAS_READ_TIMEOUT);
}

#ifdef CONFIG_PSTORE
static int nvram_pstore_open(struct pstore_info *psi)
{
	/* Reset the iterator to start reading partitions again */
	read_type = -1;
	return 0;
}

/**
 * nvram_pstore_write - pstore write callback for nvram
 * @type:               Type of message logged
 * @reason:             reason behind dump (oops/panic)
 * @id:                 identifier to indicate the write performed
 * @part:               pstore writes data to registered buffer in parts,
 *                      part number will indicate the same.
 * @count:              Indicates oops count
 * @size:               number of bytes written to the registered buffer
 * @psi:                registered pstore_info structure
 *
 * Called by pstore_dump() when an oops or panic report is logged in the
 * printk buffer.
 * Returns 0 on successful write.
 */
static int nvram_pstore_write(enum pstore_type_id type,
				enum kmsg_dump_reason reason,
				u64 *id, unsigned int part, int count,
				size_t size, struct pstore_info *psi)
{
	int rc;
	struct oops_log_info *oops_hdr = (struct oops_log_info *) oops_buf;

	/* part 1 has the recent messages from printk buffer */
	if (part > 1 || type != PSTORE_TYPE_DMESG ||
				clobbering_unread_rtas_event())
		return -1;

	oops_hdr->version = OOPS_HDR_VERSION;
	oops_hdr->report_length = (u16) size;
	oops_hdr->timestamp = get_seconds();
	rc = nvram_write_os_partition(&oops_log_partition, oops_buf,
		(int) (sizeof(*oops_hdr) + size), ERR_TYPE_KERNEL_PANIC,
		count);

	if (rc != 0)
		return rc;

	*id = part;
	return 0;
}

/*
 * Reads the oops/panic report, rtas, of-config and common partition.
 * Returns the length of the data we read from each partition.
 * Returns 0 if we've been called before.
 */
static ssize_t nvram_pstore_read(u64 *id, enum pstore_type_id *type,
				int *count, struct timespec *time, char **buf,
				struct pstore_info *psi)
{
	struct oops_log_info *oops_hdr;
	unsigned int err_type, id_no, size = 0;
	struct nvram_os_partition *part = NULL;
	char *buff = NULL;
	int sig = 0;
	loff_t p;

	read_type++;

	switch (nvram_type_ids[read_type]) {
	case PSTORE_TYPE_DMESG:
		part = &oops_log_partition;
		*type = PSTORE_TYPE_DMESG;
		break;
	case PSTORE_TYPE_PPC_RTAS:
		part = &rtas_log_partition;
		*type = PSTORE_TYPE_PPC_RTAS;
		time->tv_sec = last_rtas_event;
		time->tv_nsec = 0;
		break;
	case PSTORE_TYPE_PPC_OF:
		sig = NVRAM_SIG_OF;
		part = &of_config_partition;
		*type = PSTORE_TYPE_PPC_OF;
		*id = PSTORE_TYPE_PPC_OF;
		time->tv_sec = 0;
		time->tv_nsec = 0;
		break;
	case PSTORE_TYPE_PPC_COMMON:
		sig = NVRAM_SIG_SYS;
		part = &common_partition;
		*type = PSTORE_TYPE_PPC_COMMON;
		*id = PSTORE_TYPE_PPC_COMMON;
		time->tv_sec = 0;
		time->tv_nsec = 0;
		break;
	default:
		return 0;
	}

	if (!part->os_partition) {
		p = nvram_find_partition2(part->name, sig, &size);
		if (p <= 0) {
			pr_err("nvram: Failed to find partition %s, "
				"err %d\n", part->name, (int)p);
			return 0;
		}
		part->index = p;
		part->size = size;
	}

	buff = kmalloc(part->size, GFP_KERNEL);

	if (!buff)
		return -ENOMEM;

	if (nvram_read_partition(part, buff, part->size, &err_type, &id_no)) {
		kfree(buff);
		return 0;
	}

	*count = 0;

	if (part->os_partition)
		*id = id_no;

	if (nvram_type_ids[read_type] == PSTORE_TYPE_DMESG) {
		int length;
		size_t hdr_size;

		oops_hdr = (struct oops_log_info *)buff;
		if (oops_hdr->version < OOPS_HDR_VERSION) {
			hdr_size = sizeof(u16);
			length = oops_hdr->version;
			time->tv_sec = 0;
			time->tv_nsec = 0;
		} else {
			hdr_size = sizeof(*oops_hdr);
			length = oops_hdr->report_length;
			time->tv_sec = oops_hdr->timestamp;
			time->tv_nsec = 0;
		}

		*buf = kmalloc(length, GFP_KERNEL);
		if (*buf == NULL)
			return -ENOMEM;
		memcpy(*buf, buff + hdr_size, length);
		kfree(buff);
		return length;
	}

	*buf = buff;
	return part->size;
}

static struct pstore_info nvram_pstore_info = {
	.owner = THIS_MODULE,
	.name = "nvram",
	.open = nvram_pstore_open,
	.read = nvram_pstore_read,
	.write = nvram_pstore_write,
};

static int nvram_pstore_init(void)
{
	int rc = 0;

	nvram_pstore_info.buf = oops_data;
	nvram_pstore_info.bufsize = oops_data_sz;

	rc = pstore_register(&nvram_pstore_info);
	if (rc != 0)
		pr_err("nvram: pstore_register() failed, defaults to "
				"kmsg_dump; returned %d\n", rc);

	return rc;
}
#else
static int nvram_pstore_init(void)
{
	return -1;
}
#endif

static void __init nvram_init_oops_partition(int rtas_partition_exists)
{
	int rc;

	rc = pseries_nvram_init_os_partition(&oops_log_partition);
	if (rc != 0) {
		if (!rtas_partition_exists)
			return;
		pr_notice("nvram: Using %s partition to log both"
			" RTAS errors and oops/panic reports\n",
			rtas_log_partition.name);
		memcpy(&oops_log_partition, &rtas_log_partition,
						sizeof(rtas_log_partition));
	}
	oops_buf = kmalloc(oops_log_partition.size, GFP_KERNEL);
	if (!oops_buf) {
		pr_err("nvram: No memory for %s partition\n",
						 oops_log_partition.name);
		return;
	}
	oops_data = oops_buf + sizeof(struct oops_log_info);
	oops_data_sz = oops_log_partition.size - sizeof(struct oops_log_info);

	rc = nvram_pstore_init();

	if (!rc)
		return;

	rc = kmsg_dump_register(&nvram_kmsg_dumper);
	if (rc != 0) {
		pr_err("nvram: kmsg_dump_register() failed; returned %d\n", rc);
		kfree(oops_buf);
		return;
	}
}

static int __init pseries_nvram_init_log_partitions(void)
{
	int rc;

	rc = pseries_nvram_init_os_partition(&rtas_log_partition);
	nvram_init_oops_partition(rc == 0);
	return 0;
}
machine_arch_initcall(pseries, pseries_nvram_init_log_partitions);

int __init pSeries_nvram_init(void)
{
	struct device_node *nvram;
	const unsigned int *nbytes_p;
	unsigned int proplen;

	nvram = of_find_node_by_type(NULL, "nvram");
	if (nvram == NULL)
		return -ENODEV;

	nbytes_p = of_get_property(nvram, "#bytes", &proplen);
	if (nbytes_p == NULL || proplen != sizeof(unsigned int)) {
		of_node_put(nvram);
		return -EIO;
	}

	nvram_size = *nbytes_p;

	nvram_fetch = rtas_token("nvram-fetch");
	nvram_store = rtas_token("nvram-store");
	printk(KERN_INFO "PPC64 nvram contains %d bytes\n", nvram_size);
	of_node_put(nvram);

	ppc_md.nvram_read	= pSeries_nvram_read;
	ppc_md.nvram_write	= pSeries_nvram_write;
	ppc_md.nvram_size	= pSeries_nvram_get_size;

	return 0;
}

/*
 * Try to capture the last capture_len bytes of the printk buffer.  Return
 * the amount actually captured.
 */
static size_t capture_last_msgs(const char *old_msgs, size_t old_len,
				const char *new_msgs, size_t new_len,
				char *captured, size_t capture_len)
{
	if (new_len >= capture_len) {
		memcpy(captured, new_msgs + (new_len - capture_len),
								capture_len);
		return capture_len;
	} else {
		/* Grab the end of old_msgs. */
		size_t old_tail_len = min(old_len, capture_len - new_len);
		memcpy(captured, old_msgs + (old_len - old_tail_len),
								old_tail_len);
		memcpy(captured + old_tail_len, new_msgs, new_len);
		return old_tail_len + new_len;
	}
}


/* our kmsg_dump callback */
static void oops_to_nvram(struct kmsg_dumper *dumper,
		enum kmsg_dump_reason reason,
		const char *old_msgs, unsigned long old_len,
		const char *new_msgs, unsigned long new_len)
{
	struct oops_log_info *oops_hdr = (struct oops_log_info *)oops_buf;
	static unsigned int oops_count = 0;
	size_t text_len;

	if (clobbering_unread_rtas_event())
		return;

	text_len = capture_last_msgs(old_msgs, old_len, new_msgs, new_len,
					oops_data, oops_data_sz);
	oops_hdr->version = OOPS_HDR_VERSION;
	oops_hdr->report_length = (u16) text_len;
	oops_hdr->timestamp = get_seconds();

	nvram_write_os_partition(&oops_log_partition, oops_buf,
				(int) (sizeof(*oops_hdr) + text_len),
				ERR_TYPE_KERNEL_PANIC, ++oops_count);
}
