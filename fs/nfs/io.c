/*
 * Copyright (c) 2016 Trond Myklebust
 *
 * I/O and data path helper functionality.
 */

#include <linux/types.h>
#include <linux/kernel.h>
#include <linux/bitops.h>
#include <linux/rwsem.h>
#include <linux/fs.h>
#include <linux/nfs_fs.h>

#include "internal.h"

/* Call with exclusively locked inode->i_rwsem */
static void nfs_block_o_direct(struct nfs_inode *nfsi, struct inode *inode)
{
	if (test_bit(NFS_INO_ODIRECT, &nfsi->flags)) {
		clear_bit(NFS_INO_ODIRECT, &nfsi->flags);
		inode_dio_wait(inode);
	}
}

/**
 * nfs_start_io_read - declare the file is being used for buffered reads
 * @inode - file inode
 *
 * Declare that a buffered read operation is about to start, and ensure
 * that we block all direct I/O.
 * On exit, the function ensures that the NFS_INO_ODIRECT flag is unset,
 * and holds a lock on inode->i_mutex.
 * Note that buffered writes and truncates both take i_mutex, meaning that
 * those are serialised w.r.t. the reads.
 */
void
nfs_start_io_read(struct inode *inode)
{
	struct nfs_inode *nfsi = NFS_I(inode);

	if (test_bit(NFS_INO_ODIRECT, &nfsi->flags) != 0) {
		mutex_lock(&inode->i_mutex);
		nfs_block_o_direct(nfsi, inode);
		mutex_unlock(&inode->i_mutex);
	}
}

/**
 * nfs_start_io_write - declare the file is being used for buffered writes
 * @inode - file inode
 *
 * Declare that a buffered write operation is about to start, and ensure
 * that we block all direct I/O.
 */
void
nfs_start_io_write(struct inode *inode)
{
	mutex_lock(&inode->i_mutex);
	nfs_block_o_direct(NFS_I(inode), inode);
}

/**
 * nfs_end_io_write - declare that the buffered write operation is done
 * @inode - file inode
 *
 * Declare that a buffered write operation is done, and release the
 * locks.
 */
void
nfs_end_io_write(struct inode *inode)
{
	mutex_unlock(&inode->i_mutex);
}

/* Call with exclusively locked inode->i_mutex */
static void nfs_block_buffered(struct nfs_inode *nfsi, struct inode *inode)
{
	if (!test_bit(NFS_INO_ODIRECT, &nfsi->flags)) {
		set_bit(NFS_INO_ODIRECT, &nfsi->flags);
		nfs_sync_mapping(inode->i_mapping);
	}
}

/**
 * nfs_end_io_direct - declare the file is being used for direct i/o
 * @inode - file inode
 *
 * Declare that a direct I/O operation is about to start, and ensure
 * that we block all buffered I/O.
 * On exit, the function ensures that the NFS_INO_ODIRECT flag is set,
 * and holds a lock on i_mutex to ensure that the flag cannot be
 * changed.
 * Note that buffered writes and truncates both take i_mutex,
 * meaning that those are serialised w.r.t. O_DIRECT.
 */
void
nfs_start_io_direct(struct inode *inode)
{
	struct nfs_inode *nfsi = NFS_I(inode);

	mutex_lock(&inode->i_mutex);
	if (test_bit(NFS_INO_ODIRECT, &nfsi->flags) == 0)
		nfs_block_buffered(nfsi, inode);
}

/**
 * nfs_end_io_direct - declare that the direct i/o operation is done
 * @inode - file inode
 *
 * Declare that a direct I/O operation is done, and release i_mutex
 */
void
nfs_end_io_direct(struct inode *inode)
{
	mutex_unlock(&inode->i_mutex);
}
