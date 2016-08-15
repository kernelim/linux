/*
 * Copyright (C) 2015 Red Hat
 *
 * This file is subject to the terms and conditions of the GNU General Public
 * License v2. See the file COPYING in the main directory of this archive for
 * more details.
 */

#include <drm/drm_backport.h>


/*
 * alloc_anon_inode
 */

static const struct file_operations anon_inode_fops;

/*
 * nop .set_page_dirty method so that people can use .page_mkwrite on
 * anon inodes.
 */
static int anon_set_page_dirty(struct page *page)
{
	return 0;
};

static const struct address_space_operations anon_aops = {
	.set_page_dirty = anon_set_page_dirty,
};

struct inode *alloc_anon_inode(struct super_block *mnt_sb)
{
	struct inode *inode = new_inode(mnt_sb);

	if (!inode)
		return ERR_PTR(-ENOMEM);

	inode->i_fop = &anon_inode_fops;

	inode->i_mapping->a_ops = &anon_aops;

	/*
	 * Mark the inode dirty from the very beginning,
	 * that way it will never be moved to the dirty
	 * list because mark_inode_dirty() will think
	 * that it already _is_ on the dirty list.
	 */
	inode->i_state = I_DIRTY;
	inode->i_mode = S_IFREG | S_IRUSR | S_IWUSR;
	inode->i_uid = current_fsuid();
	inode->i_gid = current_fsgid();
	inode->i_atime = inode->i_mtime = inode->i_ctime = CURRENT_TIME;
	return inode;
}


/*
 * simple_dname
 */

static int prepend(char **buffer, int *buflen, const char *str, int namelen)
{
	*buflen -= namelen;
	if (*buflen < 0)
		return -ENAMETOOLONG;
	*buffer -= namelen;
	memcpy(*buffer, str, namelen);
	return 0;
}

char *simple_dname(struct dentry *dentry, char *buffer, int buflen)
{
	char *end = buffer + buflen;
	/* these dentries are never renamed, so d_lock is not needed */
	if (prepend(&end, &buflen, " (deleted)", 11) ||
	    prepend(&end, &buflen, dentry->d_name.name, dentry->d_name.len) ||
	    prepend(&end, &buflen, "/", 1))
		end = ERR_PTR(-ENAMETOOLONG);
	return end;
}

/*
 * shrinker
 */

#undef shrinker
#undef register_shrinker
#undef unregister_shrinker

static int shrinker2_shrink(struct shrinker *shrinker, int nr_to_scan, gfp_t gfp_mask)
{
	struct shrinker2 *s2 = container_of(shrinker, struct shrinker2, compat);
	struct shrink_control sc = {
			.nr_to_scan = nr_to_scan,
			.gfp_mask = gfp_mask,
	};
	int count;

	s2->scan_objects(s2, &sc);
	count = s2->count_objects(s2, &sc);
	shrinker->seeks = s2->seeks;

	return count;
}

void register_shrinker2(struct shrinker2 *s2)
{
	s2->compat.shrink = shrinker2_shrink;
	s2->compat.seeks = s2->seeks;
	register_shrinker(&s2->compat);
}
EXPORT_SYMBOL(register_shrinker2);

void unregister_shrinker2(struct shrinker2 *s2)
{
	unregister_shrinker(&s2->compat);
}
EXPORT_SYMBOL(unregister_shrinker2);


/*
 *
 */

int __init drm_backport_init(void)
{
	return 0;
}

void __exit drm_backport_exit(void)
{
}
