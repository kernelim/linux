// SPDX-License-Identifier: GPL-2.0
/*
 * Copyright (C) 2017 Red Hat, Inc.
 * Copyright (c) 2018-2021 Christoph Hellwig.
 */
#include <linux/module.h>
#include <linux/compiler.h>
#include <linux/fs.h>
#include <linux/iomap.h>
#include <linux/pagemap.h>
#include <linux/pagevec.h>

/*
 * Seek for SEEK_DATA / SEEK_HOLE within @page, starting at @lastoff.
 * Returns true if found and updates @lastoff to the offset in file.
 */
static bool
page_seek_hole_data(struct inode *inode, struct page *page, loff_t *lastoff,
		int whence)
{
	const struct address_space_operations *ops = inode->i_mapping->a_ops;
	unsigned int bsize = i_blocksize(inode), off;
	bool seek_data = whence == SEEK_DATA;
	loff_t poff = page_offset(page);

	if (WARN_ON_ONCE(*lastoff >= poff + PAGE_SIZE))
		return false;

	if (*lastoff < poff) {
		/*
		 * Last offset smaller than the start of the page means we found
		 * a hole:
		 */
		if (whence == SEEK_HOLE)
			return true;
		*lastoff = poff;
	}

	/*
	 * Just check the page unless we can and should check block ranges:
	 */
	if (bsize == PAGE_SIZE || !ops->is_partially_uptodate)
		return PageUptodate(page) == seek_data;

	lock_page(page);
	if (unlikely(page->mapping != inode->i_mapping))
		goto out_unlock_not_found;

	for (off = 0; off < PAGE_SIZE; off += bsize) {
		if (offset_in_page(*lastoff) >= off + bsize)
			continue;
		if (ops->is_partially_uptodate(page, off, bsize) == seek_data) {
			unlock_page(page);
			return true;
		}
		*lastoff = poff + off + bsize;
	}

out_unlock_not_found:
	unlock_page(page);
	return false;
}

/*
 * Seek for SEEK_DATA / SEEK_HOLE in the page cache.
 *
 * Within unwritten extents, the page cache determines which parts are holes
 * and which are data: uptodate buffer heads count as data; everything else
 * counts as a hole.
 *
 * Returns the resulting offset on successs, and -ENOENT otherwise.
 */
loff_t
page_cache_seek_hole_data(struct inode *inode, loff_t offset, loff_t length,
		int whence)
{
	pgoff_t index = offset >> PAGE_SHIFT;
	pgoff_t end = DIV_ROUND_UP(offset + length, PAGE_SIZE);
	loff_t lastoff = offset;
	struct pagevec pvec;

	if (length <= 0)
		return -ENOENT;

	pagevec_init(&pvec);

	do {
		unsigned nr_pages, i;

		nr_pages = pagevec_lookup_range(&pvec, inode->i_mapping, &index,
						end - 1);
		if (nr_pages == 0)
			break;

		for (i = 0; i < nr_pages; i++) {
			struct page *page = pvec.pages[i];

			if (page_seek_hole_data(inode, page, &lastoff, whence))
				goto check_range;
			lastoff = page_offset(page) + PAGE_SIZE;
		}
		pagevec_release(&pvec);
	} while (index < end);

	/* When no page at lastoff and we are not done, we found a hole. */
	if (whence != SEEK_HOLE)
		goto not_found;

check_range:
	if (lastoff < offset + length)
		goto out;
not_found:
	lastoff = -ENOENT;
out:
	pagevec_release(&pvec);
	return lastoff;
}
EXPORT_SYMBOL_GPL(page_cache_seek_hole_data);


static loff_t iomap_seek_hole_iter(const struct iomap_iter *iter,
		loff_t *hole_pos)
{
	loff_t length = iomap_length(iter);

	switch (iter->iomap.type) {
	case IOMAP_UNWRITTEN:
		*hole_pos = page_cache_seek_hole_data(iter->inode,
				iter->pos, length, SEEK_HOLE);
		if (*hole_pos < 0)
			return length;
		return 0;
	case IOMAP_HOLE:
		*hole_pos = iter->pos;
		return 0;
	default:
		return length;
	}
}

loff_t
iomap_seek_hole(struct inode *inode, loff_t pos, const struct iomap_ops *ops)
{
	loff_t size = i_size_read(inode);
	struct iomap_iter iter = {
		.inode	= inode,
		.pos	= pos,
		.flags	= IOMAP_REPORT,
	};
	int ret;

	/* Nothing to be found before or beyond the end of the file. */
	if (pos < 0 || pos >= size)
		return -ENXIO;

	iter.len = size - pos;
	while ((ret = iomap_iter(&iter, ops)) > 0)
		iter.processed = iomap_seek_hole_iter(&iter, &pos);
	if (ret < 0)
		return ret;
	if (iter.len) /* found hole before EOF */
		return pos;
	return size;
}
EXPORT_SYMBOL_GPL(iomap_seek_hole);

static loff_t iomap_seek_data_iter(const struct iomap_iter *iter,
		loff_t *hole_pos)
{
	loff_t length = iomap_length(iter);

	switch (iter->iomap.type) {
	case IOMAP_HOLE:
		return length;
	case IOMAP_UNWRITTEN:
		*hole_pos = page_cache_seek_hole_data(iter->inode,
				iter->pos, length, SEEK_DATA);
		if (*hole_pos < 0)
			return length;
		return 0;
	default:
		*hole_pos = iter->pos;
		return 0;
	}
}

loff_t
iomap_seek_data(struct inode *inode, loff_t pos, const struct iomap_ops *ops)
{
	loff_t size = i_size_read(inode);
	struct iomap_iter iter = {
		.inode	= inode,
		.pos	= pos,
		.flags	= IOMAP_REPORT,
	};
	int ret;

	/* Nothing to be found before or beyond the end of the file. */
	if (pos < 0 || pos >= size)
		return -ENXIO;

	iter.len = size - pos;
	while ((ret = iomap_iter(&iter, ops)) > 0)
		iter.processed = iomap_seek_data_iter(&iter, &pos);
	if (ret < 0)
		return ret;
	if (iter.len) /* found data before EOF */
		return pos;
	/* We've reached the end of the file without finding data */
	return -ENXIO;
}
EXPORT_SYMBOL_GPL(iomap_seek_data);
