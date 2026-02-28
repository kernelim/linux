/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_FS_STRUCT_H
#define _LINUX_FS_STRUCT_H

#include <linux/path.h>
#include <linux/spinlock.h>
#include <linux/seqlock.h>

struct fs_struct {
	int users;
	spinlock_t lock;
	seqcount_t seq;
	int umask;
	int in_exec;
	RH_KABI_FILL_HOLE(int pwd_refs)	/* A pool of extra pwd references */
	struct path root, pwd;
} __randomize_layout;

extern struct kmem_cache *fs_cachep;

extern void exit_fs(struct task_struct *);
extern void set_fs_root(struct fs_struct *, const struct path *);
extern void set_fs_pwd(struct fs_struct *, const struct path *);
extern struct fs_struct *copy_fs_struct(struct fs_struct *);
extern void free_fs_struct(struct fs_struct *);
extern int unshare_fs_struct(void);

static inline void get_fs_root(struct fs_struct *fs, struct path *root)
{
	spin_lock(&fs->lock);
	*root = fs->root;
	path_get(root);
	spin_unlock(&fs->lock);
}

static inline void get_fs_pwd(struct fs_struct *fs, struct path *pwd)
{
	spin_lock(&fs->lock);
	*pwd = fs->pwd;
	path_get(pwd);
	spin_unlock(&fs->lock);
}

/* Acquire a pwd reference from the pwd_refs pool, if available */
static inline void get_fs_pwd_pool(struct fs_struct *fs, struct path *pwd)
{
	spin_lock(&fs->lock);
	*pwd = fs->pwd;
	if (fs->pwd_refs)
		fs->pwd_refs--;
	else
		path_get(pwd);
	spin_unlock(&fs->lock);
}

/* Release a pwd reference back to the pwd_refs pool, if appropriate */
static inline void put_fs_pwd_pool(struct fs_struct *fs, struct path *pwd)
{
	bool put = false;

	spin_lock(&fs->lock);
	if ((fs->pwd.dentry == pwd->dentry) && (fs->pwd.mnt == pwd->mnt))
		fs->pwd_refs++;
	else
		put = true;
	spin_unlock(&fs->lock);
	if (put)
		path_put(pwd);
}

extern bool current_chrooted(void);

#endif /* _LINUX_FS_STRUCT_H */
