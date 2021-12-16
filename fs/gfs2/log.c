/*
 * Copyright (C) Sistina Software, Inc.  1997-2003 All rights reserved.
 * Copyright (C) 2004-2007 Red Hat, Inc.  All rights reserved.
 *
 * This copyrighted material is made available to anyone wishing to use,
 * modify, copy, or redistribute it subject to the terms and conditions
 * of the GNU General Public License version 2.
 */

#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/completion.h>
#include <linux/buffer_head.h>
#include <linux/gfs2_ondisk.h>
#include <linux/crc32.h>
#include <linux/delay.h>
#include <linux/kthread.h>
#include <linux/freezer.h>
#include <linux/bio.h>
#include <linux/writeback.h>
#include <linux/list_sort.h>

#include "gfs2.h"
#include "incore.h"
#include "bmap.h"
#include "glock.h"
#include "log.h"
#include "lops.h"
#include "meta_io.h"
#include "util.h"
#include "dir.h"
#include "trace_gfs2.h"

/**
 * gfs2_struct2blk - compute stuff
 * @sdp: the filesystem
 * @nstruct: the number of structures
 * @ssize: the size of the structures
 *
 * Compute the number of log descriptor blocks needed to hold a certain number
 * of structures of a certain size.
 *
 * Returns: the number of blocks needed (minimum is always 1)
 */

unsigned int gfs2_struct2blk(struct gfs2_sbd *sdp, unsigned int nstruct,
			     unsigned int ssize)
{
	unsigned int blks;
	unsigned int first, second;

	blks = 1;
	first = (sdp->sd_sb.sb_bsize - sizeof(struct gfs2_log_descriptor)) / ssize;

	if (nstruct > first) {
		second = (sdp->sd_sb.sb_bsize -
			  sizeof(struct gfs2_meta_header)) / ssize;
		blks += DIV_ROUND_UP(nstruct - first, second);
	}

	return blks;
}

/**
 * gfs2_remove_from_ail - Remove an entry from the ail lists, updating counters
 * @mapping: The associated mapping (maybe NULL)
 * @bd: The gfs2_bufdata to remove
 *
 * The ail lock _must_ be held when calling this function
 *
 */

void gfs2_remove_from_ail(struct gfs2_bufdata *bd)
{
	bd->bd_tr = NULL;
	list_del_init(&bd->bd_ail_st_list);
	list_del_init(&bd->bd_ail_gl_list);
	atomic_dec(&bd->bd_gl->gl_ail_count);
	brelse(bd->bd_bh);
}

/**
 * gfs2_ail1_start_one - Start I/O on a part of the AIL
 * @sdp: the filesystem
 * @wbc: The writeback control structure
 * @ai: The ail structure
 *
 */

static int gfs2_ail1_start_one(struct gfs2_sbd *sdp,
			       struct writeback_control *wbc,
			       struct gfs2_trans *tr)
__releases(&sdp->sd_ail_lock)
__acquires(&sdp->sd_ail_lock)
{
	struct gfs2_glock *gl = NULL;
	struct address_space *mapping;
	struct gfs2_bufdata *bd, *s;
	struct buffer_head *bh;
	int ret = 0;

	list_for_each_entry_safe_reverse(bd, s, &tr->tr_ail1_list, bd_ail_st_list) {
		bh = bd->bd_bh;

		gfs2_assert(sdp, bd->bd_tr == tr);

		if (!buffer_busy(bh)) {
			if (buffer_uptodate(bh)) {
				list_move(&bd->bd_ail_st_list,
					  &tr->tr_ail2_list);
				continue;
			}
			if (!cmpxchg(&sdp->sd_log_error, 0, -EIO)) {
				gfs2_io_error_bh(sdp, bh);
				gfs2_withdraw_delayed(sdp);
			}
		}

		if (gfs2_withdrawn(sdp)) {
			gfs2_remove_from_ail(bd);
			continue;
		}
		if (!buffer_dirty(bh))
			continue;
		if (gl == bd->bd_gl)
			continue;
		gl = bd->bd_gl;
		list_move(&bd->bd_ail_st_list, &tr->tr_ail1_list);
		mapping = bh->b_page->mapping;
		if (!mapping)
			continue;
		spin_unlock(&sdp->sd_ail_lock);
		ret = generic_writepages(mapping, wbc);
		spin_lock(&sdp->sd_ail_lock);
		if (ret || wbc->nr_to_write <= 0)
			break;
		return -EBUSY;
	}

	return ret;
}


/**
 * gfs2_ail1_flush - start writeback of some ail1 entries 
 * @sdp: The super block
 * @wbc: The writeback control structure
 *
 * Writes back some ail1 entries, according to the limits in the
 * writeback control structure
 */

void gfs2_ail1_flush(struct gfs2_sbd *sdp, struct writeback_control *wbc)
{
	struct list_head *head = &sdp->sd_ail1_list;
	struct gfs2_trans *tr;
	int ret;

	trace_gfs2_ail_flush(sdp, wbc, 1);
	spin_lock(&sdp->sd_ail_lock);
restart:
	ret = 0;
	list_for_each_entry_reverse(tr, head, tr_list) {
		if (wbc->nr_to_write <= 0)
			break;
		ret = gfs2_ail1_start_one(sdp, wbc, tr);
		if (ret) {
			if (ret == -EBUSY)
				goto restart;
			break;
		}
	}
	spin_unlock(&sdp->sd_ail_lock);
	if (ret) {
		gfs2_lm(sdp, "gfs2_ail1_start_one (generic_writepages) "
			"returned: %d\n", ret);
		gfs2_withdraw(sdp);
	}
	trace_gfs2_ail_flush(sdp, wbc, 0);
}

/**
 * gfs2_ail1_start - start writeback of all ail1 entries
 * @sdp: The superblock
 */

static void gfs2_ail1_start(struct gfs2_sbd *sdp)
{
	struct writeback_control wbc = {
		.sync_mode = WB_SYNC_NONE,
		.nr_to_write = LONG_MAX,
		.range_start = 0,
		.range_end = LLONG_MAX,
	};

	return gfs2_ail1_flush(sdp, &wbc);
}

/**
 * gfs2_ail1_empty_one - Check whether or not a trans in the AIL has been synced
 * @sdp: the filesystem
 * @tr: the transaction
 * @max_revokes: If nonzero, issue revokes for the bd items for written buffers
 *
 */

static void gfs2_ail1_empty_one(struct gfs2_sbd *sdp, struct gfs2_trans *tr,
				int *max_revokes)
{
	struct gfs2_bufdata *bd, *s;
	struct buffer_head *bh;

	list_for_each_entry_safe_reverse(bd, s, &tr->tr_ail1_list,
					 bd_ail_st_list) {
		bh = bd->bd_bh;
		gfs2_assert(sdp, bd->bd_tr == tr);
		/*
		 * If another process flagged an io error, e.g. writing to the
		 * journal, error all other bhs and move them off the ail1 to
		 * prevent a tight loop when unmount tries to flush ail1,
		 * regardless of whether they're still busy. If no outside
		 * errors were found and the buffer is busy, move to the next.
		 * If the ail buffer is not busy and caught an error, flag it
		 * for others.
		 */
		if (!sdp->sd_log_error && buffer_busy(bh))
			continue;
		if (!buffer_uptodate(bh) &&
		    !cmpxchg(&sdp->sd_log_error, 0, -EIO)) {
			gfs2_io_error_bh(sdp, bh);
			gfs2_withdraw_delayed(sdp);
		}
		/*
		 * If we have space for revokes and the bd is no longer on any
		 * buf list, we can just add a revoke for it immediately and
		 * avoid having to put it on the ail2 list, where it would need
		 * to be revoked later.
		 */
		if (*max_revokes && list_empty(&bd->bd_list)) {
			gfs2_add_revoke(sdp, bd);
			(*max_revokes)--;
			continue;
		}
		list_move(&bd->bd_ail_st_list, &tr->tr_ail2_list);
	}
}

/**
 * gfs2_ail1_empty - Try to empty the ail1 lists
 * @sdp: The superblock
 * @max_revokes: If non-zero, add revokes where appropriate
 *
 * Tries to empty the ail1 lists, starting with the oldest first
 */

static int gfs2_ail1_empty(struct gfs2_sbd *sdp, int max_revokes)
{
	struct gfs2_trans *tr, *s;
	int oldest_tr = 1;
	int ret;

	spin_lock(&sdp->sd_ail_lock);
	list_for_each_entry_safe_reverse(tr, s, &sdp->sd_ail1_list, tr_list) {
		gfs2_ail1_empty_one(sdp, tr, &max_revokes);
		if (list_empty(&tr->tr_ail1_list) && oldest_tr)
			list_move(&tr->tr_list, &sdp->sd_ail2_list);
		else
			oldest_tr = 0;
	}
	ret = list_empty(&sdp->sd_ail1_list);
	spin_unlock(&sdp->sd_ail_lock);

	if (test_bit(SDF_WITHDRAWING, &sdp->sd_flags)) {
		gfs2_lm(sdp, "fatal: I/O error(s)\n");
		gfs2_withdraw(sdp);
	}

	return ret;
}

static void gfs2_ail1_wait(struct gfs2_sbd *sdp)
{
	struct gfs2_trans *tr;
	struct gfs2_bufdata *bd;
	struct buffer_head *bh;

	spin_lock(&sdp->sd_ail_lock);
	list_for_each_entry_reverse(tr, &sdp->sd_ail1_list, tr_list) {
		list_for_each_entry(bd, &tr->tr_ail1_list, bd_ail_st_list) {
			bh = bd->bd_bh;
			if (!buffer_locked(bh))
				continue;
			get_bh(bh);
			spin_unlock(&sdp->sd_ail_lock);
			wait_on_buffer(bh);
			brelse(bh);
			return;
		}
	}
	spin_unlock(&sdp->sd_ail_lock);
}

/**
 * gfs2_ail_empty_tr - empty one of the ail lists for a transaction
 */

static void gfs2_ail_empty_tr(struct gfs2_sbd *sdp, struct gfs2_trans *tr,
			      struct list_head *head)
{
	struct gfs2_bufdata *bd;

	while (!list_empty(head)) {
		bd = list_first_entry(head, struct gfs2_bufdata,
				      bd_ail_st_list);
		gfs2_assert(sdp, bd->bd_tr == tr);
		gfs2_remove_from_ail(bd);
	}
}

static void ail2_empty(struct gfs2_sbd *sdp, unsigned int new_tail)
{
	struct gfs2_trans *tr, *safe;
	unsigned int old_tail = sdp->sd_log_tail;
	int wrap = (new_tail < old_tail);
	int a, b, rm;

	spin_lock(&sdp->sd_ail_lock);

	list_for_each_entry_safe(tr, safe, &sdp->sd_ail2_list, tr_list) {
		a = (old_tail <= tr->tr_first);
		b = (tr->tr_first < new_tail);
		rm = (wrap) ? (a || b) : (a && b);
		if (!rm)
			continue;

		gfs2_ail_empty_tr(sdp, tr, &tr->tr_ail2_list);
		list_del(&tr->tr_list);
		gfs2_assert_warn(sdp, list_empty(&tr->tr_ail1_list));
		gfs2_assert_warn(sdp, list_empty(&tr->tr_ail2_list));
		kfree(tr);
	}

	spin_unlock(&sdp->sd_ail_lock);
}

/**
 * gfs2_log_reserve - Make a log reservation
 * @sdp: The GFS2 superblock
 * @blks: The number of blocks to reserve
 *
 * Note that we never give out the last few blocks of the journal. Thats
 * due to the fact that there is a small number of header blocks
 * associated with each log flush. The exact number can't be known until
 * flush time, so we ensure that we have just enough free blocks at all
 * times to avoid running out during a log flush.
 *
 * We no longer flush the log here, instead we wake up logd to do that
 * for us. To avoid the thundering herd and to ensure that we deal fairly
 * with queued waiters, we use an exclusive wait. This means that when we
 * get woken with enough journal space to get our reservation, we need to
 * wake the next waiter on the list.
 *
 * Returns: errno
 */

int gfs2_log_reserve(struct gfs2_sbd *sdp, unsigned int blks)
{
	unsigned reserved_blks = 7 * (4096 / sdp->sd_vfs->s_blocksize);
	unsigned wanted = blks + reserved_blks;
	DEFINE_WAIT(wait);
	int did_wait = 0;
	unsigned int free_blocks;

	if (gfs2_assert_warn(sdp, blks) ||
	    gfs2_assert_warn(sdp, blks <= sdp->sd_jdesc->jd_blocks))
		return -EINVAL;
	atomic_add(blks, &sdp->sd_log_blks_needed);
retry:
	free_blocks = atomic_read(&sdp->sd_log_blks_free);
	if (unlikely(free_blocks <= wanted)) {
		do {
			prepare_to_wait_exclusive(&sdp->sd_log_waitq, &wait,
					TASK_UNINTERRUPTIBLE);
			wake_up(&sdp->sd_logd_waitq);
			did_wait = 1;
			if (atomic_read(&sdp->sd_log_blks_free) <= wanted)
				io_schedule();
			free_blocks = atomic_read(&sdp->sd_log_blks_free);
		} while(free_blocks <= wanted);
		finish_wait(&sdp->sd_log_waitq, &wait);
	}
	if (atomic_cmpxchg(&sdp->sd_log_blks_free, free_blocks,
				free_blocks - blks) != free_blocks)
		goto retry;
	atomic_sub(blks, &sdp->sd_log_blks_needed);
	trace_gfs2_log_blocks(sdp, -blks);

	/*
	 * If we waited, then so might others, wake them up _after_ we get
	 * our share of the log.
	 */
	if (unlikely(did_wait))
		wake_up(&sdp->sd_log_waitq);

	down_read(&sdp->sd_log_flush_lock);

	return 0;
}

/**
 * log_distance - Compute distance between two journal blocks
 * @sdp: The GFS2 superblock
 * @newer: The most recent journal block of the pair
 * @older: The older journal block of the pair
 *
 *   Compute the distance (in the journal direction) between two
 *   blocks in the journal
 *
 * Returns: the distance in blocks
 */

static inline unsigned int log_distance(struct gfs2_sbd *sdp, unsigned int newer,
					unsigned int older)
{
	int dist;

	dist = newer - older;
	if (dist < 0)
		dist += sdp->sd_jdesc->jd_blocks;

	return dist;
}

/**
 * calc_reserved - Calculate the number of blocks to reserve when
 *                 refunding a transaction's unused buffers.
 * @sdp: The GFS2 superblock
 *
 * This is complex.  We need to reserve room for all our currently used
 * metadata buffers (e.g. normal file I/O rewriting file time stamps) and 
 * all our journaled data buffers for journaled files (e.g. files in the 
 * meta_fs like rindex, or files for which chattr +j was done.)
 * If we don't reserve enough space, gfs2_log_refund and gfs2_log_flush
 * will count it as free space (sd_log_blks_free) and corruption will follow.
 *
 * We can have metadata bufs and jdata bufs in the same journal.  So each
 * type gets its own log header, for which we need to reserve a block.
 * In fact, each type has the potential for needing more than one header 
 * in cases where we have more buffers than will fit on a journal page.
 * Metadata journal entries take up half the space of journaled buffer entries.
 * Thus, metadata entries have buf_limit (502) and journaled buffers have
 * databuf_limit (251) before they cause a wrap around.
 *
 * Also, we need to reserve blocks for revoke journal entries and one for an
 * overall header for the lot.
 *
 * Returns: the number of blocks reserved
 */
static unsigned int calc_reserved(struct gfs2_sbd *sdp)
{
	unsigned int reserved = 0;
	unsigned int mbuf;
	unsigned int dbuf;
	struct gfs2_trans *tr = sdp->sd_log_tr;

	if (tr) {
		mbuf = tr->tr_num_buf_new - tr->tr_num_buf_rm;
		dbuf = tr->tr_num_databuf_new - tr->tr_num_databuf_rm;
		reserved = mbuf + dbuf;
		/* Account for header blocks */
		reserved += DIV_ROUND_UP(mbuf, buf_limit(sdp));
		reserved += DIV_ROUND_UP(dbuf, databuf_limit(sdp));
	}

	if (sdp->sd_log_committed_revoke > 0)
		reserved += gfs2_struct2blk(sdp, sdp->sd_log_committed_revoke,
					  sizeof(u64));
	/* One for the overall header */
	if (reserved)
		reserved++;
	return reserved;
}

static unsigned int current_tail(struct gfs2_sbd *sdp)
{
	struct gfs2_trans *tr;
	unsigned int tail;

	spin_lock(&sdp->sd_ail_lock);

	if (list_empty(&sdp->sd_ail1_list)) {
		tail = sdp->sd_log_head;
	} else {
		tr = list_last_entry(&sdp->sd_ail1_list, struct gfs2_trans,
				tr_list);
		tail = tr->tr_first;
	}

	spin_unlock(&sdp->sd_ail_lock);

	return tail;
}

static void log_pull_tail(struct gfs2_sbd *sdp, unsigned int new_tail)
{
	unsigned int dist = log_distance(sdp, new_tail, sdp->sd_log_tail);

	ail2_empty(sdp, new_tail);

	atomic_add(dist, &sdp->sd_log_blks_free);
	trace_gfs2_log_blocks(sdp, dist);
	gfs2_assert_withdraw(sdp, atomic_read(&sdp->sd_log_blks_free) <=
			     sdp->sd_jdesc->jd_blocks);

	sdp->sd_log_tail = new_tail;
}


void log_flush_wait(struct gfs2_sbd *sdp)
{
	DEFINE_WAIT(wait);

	if (atomic_read(&sdp->sd_log_in_flight)) {
		do {
			prepare_to_wait(&sdp->sd_log_flush_wait, &wait,
					TASK_UNINTERRUPTIBLE);
			if (atomic_read(&sdp->sd_log_in_flight))
				io_schedule();
		} while(atomic_read(&sdp->sd_log_in_flight));
		finish_wait(&sdp->sd_log_flush_wait, &wait);
	}
}

static int ip_cmp(void *priv, struct list_head *a, struct list_head *b)
{
	struct gfs2_inode *ipa, *ipb;

	ipa = list_entry(a, struct gfs2_inode, i_ordered);
	ipb = list_entry(b, struct gfs2_inode, i_ordered);

	if (ipa->i_no_addr < ipb->i_no_addr)
		return -1;
	if (ipa->i_no_addr > ipb->i_no_addr)
		return 1;
	return 0;
}

static void gfs2_ordered_write(struct gfs2_sbd *sdp)
{
	struct gfs2_inode *ip;
	LIST_HEAD(written);

	spin_lock(&sdp->sd_ordered_lock);
	list_sort(NULL, &sdp->sd_log_le_ordered, &ip_cmp);
	while (!list_empty(&sdp->sd_log_le_ordered)) {
		ip = list_first_entry(&sdp->sd_log_le_ordered, struct gfs2_inode,
				      i_ordered);
		list_move(&ip->i_ordered, &written);
		if (ip->i_inode.i_mapping->nrpages == 0)
			continue;
		spin_unlock(&sdp->sd_ordered_lock);
		filemap_fdatawrite(ip->i_inode.i_mapping);
		spin_lock(&sdp->sd_ordered_lock);
	}
	list_splice(&written, &sdp->sd_log_le_ordered);
	spin_unlock(&sdp->sd_ordered_lock);
}

static void gfs2_ordered_wait(struct gfs2_sbd *sdp)
{
	struct gfs2_inode *ip;

	spin_lock(&sdp->sd_ordered_lock);
	while (!list_empty(&sdp->sd_log_le_ordered)) {
		ip = list_first_entry(&sdp->sd_log_le_ordered, struct gfs2_inode,
				      i_ordered);
		list_del(&ip->i_ordered);
		WARN_ON(!test_and_clear_bit(GIF_ORDERED, &ip->i_flags));
		if (ip->i_inode.i_mapping->nrpages == 0)
			continue;
		spin_unlock(&sdp->sd_ordered_lock);
		filemap_fdatawait(ip->i_inode.i_mapping);
		spin_lock(&sdp->sd_ordered_lock);
	}
	spin_unlock(&sdp->sd_ordered_lock);
}

void gfs2_ordered_del_inode(struct gfs2_inode *ip)
{
	struct gfs2_sbd *sdp = GFS2_SB(&ip->i_inode);

	spin_lock(&sdp->sd_ordered_lock);
	if (test_and_clear_bit(GIF_ORDERED, &ip->i_flags))
		list_del(&ip->i_ordered);
	spin_unlock(&sdp->sd_ordered_lock);
}

void gfs2_add_revoke(struct gfs2_sbd *sdp, struct gfs2_bufdata *bd)
{
	struct buffer_head *bh = bd->bd_bh;
	struct gfs2_glock *gl = bd->bd_gl;

	bh->b_private = NULL;
	bd->bd_blkno = bh->b_blocknr;
	gfs2_remove_from_ail(bd); /* drops ref on bh */
	bd->bd_bh = NULL;
	bd->bd_ops = &gfs2_revoke_lops;
	sdp->sd_log_num_revoke++;
	atomic_inc(&gl->gl_revokes);
	set_bit(GLF_LFLUSH, &gl->gl_flags);
	list_add(&bd->bd_list, &sdp->sd_log_le_revoke);
}

/**
 * gfs2_write_revokes - Add as many revokes to the system transaction as we can
 * @sdp: The GFS2 superblock
 *
 * Our usual strategy is to defer writing revokes as much as we can in the hope
 * that we'll eventually overwrite the journal, which will make those revokes
 * go away.  This changes when we flush the log: at that point, there will
 * likely be some left-over space in the last revoke block of that transaction.
 * We can fill that space with additional revokes for blocks that have already
 * been written back.  This will basically come at no cost now, and will save
 * us from having to keep track of those blocks on the AIL2 list later.
 */
void gfs2_write_revokes(struct gfs2_sbd *sdp)
{
	/* number of revokes we still have room for */
	int max_revokes = (sdp->sd_sb.sb_bsize - sizeof(struct gfs2_log_descriptor)) / sizeof(u64);

	gfs2_log_lock(sdp);
	while (sdp->sd_log_num_revoke > max_revokes)
		max_revokes += (sdp->sd_sb.sb_bsize - sizeof(struct gfs2_meta_header)) / sizeof(u64);
	max_revokes -= sdp->sd_log_num_revoke;
	if (!sdp->sd_log_num_revoke) {
		atomic_dec(&sdp->sd_log_blks_free);
		/* If no blocks have been reserved, we need to also
		 * reserve a block for the header */
		if (!sdp->sd_log_blks_reserved)
			atomic_dec(&sdp->sd_log_blks_free);
	}
	gfs2_ail1_empty(sdp, max_revokes);
	gfs2_log_unlock(sdp);

	if (!sdp->sd_log_num_revoke) {
		atomic_inc(&sdp->sd_log_blks_free);
		if (!sdp->sd_log_blks_reserved)
			atomic_inc(&sdp->sd_log_blks_free);
	}
}

/**
 * log_write_header - Get and initialize a journal header buffer
 * @sdp: The GFS2 superblock
 *
 * Returns: the initialized log buffer descriptor
 */

static void log_write_header(struct gfs2_sbd *sdp, u32 flags)
{
	struct gfs2_log_header *lh;
	unsigned int tail;
	u32 hash;
	int rw = WRITE_FLUSH_FUA | REQ_META;
	struct page *page;


	if (gfs2_withdrawn(sdp)) {
		log_flush_wait(sdp);
		return;
	}

	page = mempool_alloc(gfs2_page_pool, GFP_NOIO);
	lh = page_address(page);
	clear_page(lh);

	tail = current_tail(sdp);

	lh->lh_header.mh_magic = cpu_to_be32(GFS2_MAGIC);
	lh->lh_header.mh_type = cpu_to_be32(GFS2_METATYPE_LH);
	lh->lh_header.__pad0 = cpu_to_be64(0);
	lh->lh_header.mh_format = cpu_to_be32(GFS2_FORMAT_LH);
	lh->lh_header.mh_jid = cpu_to_be32(sdp->sd_jdesc->jd_jid);
	lh->lh_sequence = cpu_to_be64(sdp->sd_log_sequence++);
	lh->lh_flags = cpu_to_be32(flags);
	lh->lh_tail = cpu_to_be32(tail);
	lh->lh_blkno = cpu_to_be32(sdp->sd_log_flush_head);
	hash = ~crc32(~0, lh, sizeof(*lh));
	lh->lh_hash = cpu_to_be32(hash);

	if (test_bit(SDF_NOBARRIERS, &sdp->sd_flags)) {
		gfs2_ordered_wait(sdp);
		log_flush_wait(sdp);
		rw = WRITE_SYNC | REQ_META | REQ_PRIO;
	}

	sdp->sd_log_idle = (tail == sdp->sd_log_flush_head);
	gfs2_log_write_page(sdp, page);
	gfs2_log_submit_bio(&sdp->sd_log_bio, rw);
	log_flush_wait(sdp);

	if (sdp->sd_log_tail != tail)
		log_pull_tail(sdp, tail);
}

/**
 * ail_drain - drain the ail lists after a withdraw
 * @sdp: Pointer to GFS2 superblock
 */
static void ail_drain(struct gfs2_sbd *sdp)
{
	struct gfs2_trans *tr;

	spin_lock(&sdp->sd_ail_lock);
	/*
	 * For transactions on the sd_ail1_list we need to drain both the
	 * ail1 and ail2 lists. That's because function gfs2_ail1_start_one
	 * (temporarily) moves items from its tr_ail1 list to tr_ail2 list
	 * before revokes are sent for that block. Items on the sd_ail2_list
	 * should have already gotten beyond that point, so no need.
	 */
	while (!list_empty(&sdp->sd_ail1_list)) {
		tr = list_first_entry(&sdp->sd_ail1_list, struct gfs2_trans,
				      tr_list);
		gfs2_ail_empty_tr(sdp, tr, &tr->tr_ail1_list);
		gfs2_ail_empty_tr(sdp, tr, &tr->tr_ail2_list);
		list_del(&tr->tr_list);
		kfree(tr);
	}
	while (!list_empty(&sdp->sd_ail2_list)) {
		tr = list_first_entry(&sdp->sd_ail2_list, struct gfs2_trans,
				      tr_list);
		gfs2_ail_empty_tr(sdp, tr, &tr->tr_ail2_list);
		list_del(&tr->tr_list);
		kfree(tr);
	}
	spin_unlock(&sdp->sd_ail_lock);
}

/**
 * gfs2_log_flush - flush incore transaction(s)
 * @sdp: the filesystem
 * @gl: The glock structure to flush.  If NULL, flush the whole incore log
 *
 */

void gfs2_log_flush(struct gfs2_sbd *sdp, struct gfs2_glock *gl)
{
	struct gfs2_trans *tr = NULL;

	down_write(&sdp->sd_log_flush_lock);

	/*
	 * Do this check while holding the log_flush_lock to prevent new
	 * buffers from being added to the ail via gfs2_pin()
	 */
	if (gfs2_withdrawn(sdp))
		goto out;

	/* Log might have been flushed while we waited for the flush lock */
	if (gl && !test_bit(GLF_LFLUSH, &gl->gl_flags)) {
		up_write(&sdp->sd_log_flush_lock);
		return;
	}
	trace_gfs2_log_flush(sdp, 1);

	tr = sdp->sd_log_tr;
	if (tr) {
		sdp->sd_log_tr = NULL;
		INIT_LIST_HEAD(&tr->tr_ail1_list);
		INIT_LIST_HEAD(&tr->tr_ail2_list);
	}

	if (gfs2_assert_withdraw_delayed(sdp,
			sdp->sd_log_num_revoke == sdp->sd_log_committed_revoke))
		goto out;

	sdp->sd_log_flush_head = sdp->sd_log_head;
	sdp->sd_log_flush_wrapped = 0;
	if (tr)
		tr->tr_first = sdp->sd_log_flush_head;

	gfs2_ordered_write(sdp);
	if (gfs2_withdrawn(sdp))
		goto out;
	lops_before_commit(sdp, tr);
	if (gfs2_withdrawn(sdp))
		goto out;
	gfs2_log_submit_bio(&sdp->sd_log_bio, WRITE);
	if (gfs2_withdrawn(sdp))
		goto out;

	if (sdp->sd_log_head != sdp->sd_log_flush_head) {
		log_flush_wait(sdp);
		log_write_header(sdp, 0);
	} else if (sdp->sd_log_tail != current_tail(sdp) && !sdp->sd_log_idle){
		if (gfs2_withdrawn(sdp))
			goto out;
		atomic_dec(&sdp->sd_log_blks_free); /* Adjust for unreserved buffer */
		trace_gfs2_log_blocks(sdp, -1);
		log_write_header(sdp, 0);
	}
	if (gfs2_withdrawn(sdp))
		goto out;
	lops_after_commit(sdp, tr);

	gfs2_log_lock(sdp);
	sdp->sd_log_head = sdp->sd_log_flush_head;
	sdp->sd_log_blks_reserved = 0;
	sdp->sd_log_committed_revoke = 0;

	spin_lock(&sdp->sd_ail_lock);
	if (tr && !list_empty(&tr->tr_ail1_list)) {
		list_add(&tr->tr_list, &sdp->sd_ail1_list);
		tr = NULL;
	}
	spin_unlock(&sdp->sd_ail_lock);
	gfs2_log_unlock(sdp);
out:
	if (gfs2_withdrawn(sdp)) {
		ail_drain(sdp); /* frees all transactions */
		tr = NULL;
	}
	trace_gfs2_log_flush(sdp, 0);
	up_write(&sdp->sd_log_flush_lock);

	kfree(tr);
}

/**
 * gfs2_merge_trans - Merge a new transaction into a cached transaction
 * @old: Original transaction to be expanded
 * @new: New transaction to be merged
 */

static void gfs2_merge_trans(struct gfs2_trans *old, struct gfs2_trans *new)
{
	WARN_ON_ONCE(!test_bit(TR_ATTACHED, &old->tr_flags));

	old->tr_num_buf_new	+= new->tr_num_buf_new;
	old->tr_num_databuf_new	+= new->tr_num_databuf_new;
	old->tr_num_buf_rm	+= new->tr_num_buf_rm;
	old->tr_num_databuf_rm	+= new->tr_num_databuf_rm;
	old->tr_num_revoke	+= new->tr_num_revoke;
	old->tr_num_revoke_rm	+= new->tr_num_revoke_rm;

	list_splice_tail_init(&new->tr_databuf, &old->tr_databuf);
	list_splice_tail_init(&new->tr_buf, &old->tr_buf);
}

static void log_refund(struct gfs2_sbd *sdp, struct gfs2_trans *tr)
{
	unsigned int reserved;
	unsigned int unused;
	unsigned int maxres;

	gfs2_log_lock(sdp);

	if (sdp->sd_log_tr) {
		gfs2_merge_trans(sdp->sd_log_tr, tr);
	} else if (tr->tr_num_buf_new || tr->tr_num_databuf_new) {
		gfs2_assert_withdraw(sdp, tr->tr_t_gh.gh_gl);
		sdp->sd_log_tr = tr;
		set_bit(TR_ATTACHED, &tr->tr_flags);
	}

	sdp->sd_log_committed_revoke += tr->tr_num_revoke - tr->tr_num_revoke_rm;
	reserved = calc_reserved(sdp);
	maxres = sdp->sd_log_blks_reserved + tr->tr_reserved;
	gfs2_assert_withdraw(sdp, maxres >= reserved);
	unused = maxres - reserved;
	atomic_add(unused, &sdp->sd_log_blks_free);
	trace_gfs2_log_blocks(sdp, unused);
	gfs2_assert_withdraw(sdp, atomic_read(&sdp->sd_log_blks_free) <=
			     sdp->sd_jdesc->jd_blocks);
	sdp->sd_log_blks_reserved = reserved;

	gfs2_log_unlock(sdp);
}

/**
 * gfs2_log_commit - Commit a transaction to the log
 * @sdp: the filesystem
 * @tr: the transaction
 *
 * We wake up gfs2_logd if the number of pinned blocks exceed thresh1
 * or the total number of used blocks (pinned blocks plus AIL blocks)
 * is greater than thresh2.
 *
 * At mount time thresh1 is 1/3rd of journal size, thresh2 is 2/3rd of
 * journal size.
 *
 * Returns: errno
 */

void gfs2_log_commit(struct gfs2_sbd *sdp, struct gfs2_trans *tr)
{
	log_refund(sdp, tr);

	if (atomic_read(&sdp->sd_log_pinned) > atomic_read(&sdp->sd_log_thresh1) ||
	    ((sdp->sd_jdesc->jd_blocks - atomic_read(&sdp->sd_log_blks_free)) >
	    atomic_read(&sdp->sd_log_thresh2)))
		wake_up(&sdp->sd_logd_waitq);
}

/**
 * gfs2_log_shutdown - write a shutdown header into a journal
 * @sdp: the filesystem
 * @ro: if the file system is being transitioned to ro
 *
 */

void gfs2_log_shutdown(struct gfs2_sbd *sdp, int ro)
{
	down_write(&sdp->sd_log_flush_lock);

	if (ro)
		clear_bit(SDF_JOURNAL_LIVE, &sdp->sd_flags);

	gfs2_assert_withdraw(sdp, !sdp->sd_log_blks_reserved);
	gfs2_assert_withdraw(sdp, !sdp->sd_log_num_revoke);
	gfs2_assert_withdraw(sdp, list_empty(&sdp->sd_ail1_list));

	sdp->sd_log_flush_head = sdp->sd_log_head;
	sdp->sd_log_flush_wrapped = 0;

	log_write_header(sdp, GFS2_LOG_HEAD_UNMOUNT);

	gfs2_assert_warn(sdp, atomic_read(&sdp->sd_log_blks_free) == sdp->sd_jdesc->jd_blocks);
	gfs2_assert_warn(sdp, sdp->sd_log_head == sdp->sd_log_tail);
	gfs2_assert_warn(sdp, list_empty(&sdp->sd_ail2_list));

	sdp->sd_log_head = sdp->sd_log_flush_head;
	sdp->sd_log_tail = sdp->sd_log_head;

	up_write(&sdp->sd_log_flush_lock);
}


/**
 * gfs2_meta_syncfs - sync all the buffers in a filesystem
 * @sdp: the filesystem
 *
 */

void gfs2_meta_syncfs(struct gfs2_sbd *sdp)
{
	gfs2_log_flush(sdp, NULL);
	for (;;) {
		gfs2_ail1_start(sdp);
		gfs2_ail1_wait(sdp);
		if (gfs2_ail1_empty(sdp, 0))
			break;
	}
	gfs2_log_flush(sdp, NULL);
}

static inline int gfs2_jrnl_flush_reqd(struct gfs2_sbd *sdp)
{
	return (atomic_read(&sdp->sd_log_pinned) +
		atomic_read(&sdp->sd_log_blks_needed) >=
		atomic_read(&sdp->sd_log_thresh1));
}

static inline int gfs2_ail_flush_reqd(struct gfs2_sbd *sdp)
{
	unsigned int used_blocks = sdp->sd_jdesc->jd_blocks - atomic_read(&sdp->sd_log_blks_free);

	if (test_and_clear_bit(SDF_FORCE_AIL_FLUSH, &sdp->sd_flags))
		return 1;

	return used_blocks + atomic_read(&sdp->sd_log_blks_needed) >=
		atomic_read(&sdp->sd_log_thresh2);
}

/**
 * gfs2_logd - Update log tail as Active Items get flushed to in-place blocks
 * @sdp: Pointer to GFS2 superblock
 *
 * Also, periodically check to make sure that we're using the most recent
 * journal index.
 */

int gfs2_logd(void *data)
{
	struct gfs2_sbd *sdp = data;
	unsigned long t = 1;
	DEFINE_WAIT(wait);
	bool did_flush;

	while (!kthread_should_stop()) {

		/* Check for errors writing to the journal */
		if (sdp->sd_log_error) {
			gfs2_lm(sdp,
				"GFS2: fsid=%s: error %d: "
				"withdrawing the file system to "
				"prevent further damage.\n",
				sdp->sd_fsname, sdp->sd_log_error);
			gfs2_withdraw(sdp);
		}

		did_flush = false;
		if (gfs2_jrnl_flush_reqd(sdp) || t == 0) {
			gfs2_ail1_empty(sdp, 0);
			gfs2_log_flush(sdp, NULL);
			did_flush = true;
		}

		if (gfs2_ail_flush_reqd(sdp)) {
			gfs2_ail1_start(sdp);
			gfs2_ail1_wait(sdp);
			gfs2_ail1_empty(sdp, 0);
			gfs2_log_flush(sdp, NULL);
			did_flush = true;
		}

		if (!gfs2_ail_flush_reqd(sdp) || did_flush)
			wake_up(&sdp->sd_log_waitq);

		t = gfs2_tune_get(sdp, gt_logd_secs) * HZ;

		try_to_freeze();

		do {
			prepare_to_wait(&sdp->sd_logd_waitq, &wait,
					TASK_INTERRUPTIBLE);
			if (!gfs2_ail_flush_reqd(sdp) &&
			    !gfs2_jrnl_flush_reqd(sdp) &&
			    !kthread_should_stop())
				t = schedule_timeout(t);
		} while(t && !gfs2_ail_flush_reqd(sdp) &&
			!gfs2_jrnl_flush_reqd(sdp) &&
			!kthread_should_stop());
		finish_wait(&sdp->sd_logd_waitq, &wait);
	}

	return 0;
}

