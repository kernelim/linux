// SPDX-License-Identifier: GPL-2.0
/*
 *  Code extracted from drivers/block/genhd.c
 *  Copyright (C) 1991-1998  Linus Torvalds
 *  Re-organised Feb 1998 Russell King
 *
 *  We now have independent partition support from the
 *  block drivers, which allows all the partition code to
 *  be grouped in one location, and it to be mostly self
 *  contained.
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/kmod.h>
#include <linux/ctype.h>
#include <linux/genhd.h>
#include <linux/blktrace_api.h>

#include RH_KABI_HIDE_INCLUDE("partitions/check.h")

const char *bdevname(struct block_device *bdev, char *buf)
{
	return disk_name(bdev->bd_disk, bdev->bd_partno, buf);
}
EXPORT_SYMBOL(bdevname);
