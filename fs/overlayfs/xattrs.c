// SPDX-License-Identifier: GPL-2.0-only

#include <linux/fs.h>
#include <linux/xattr.h>
#include <linux/posix_acl_xattr.h>
#include "overlayfs.h"

static bool ovl_is_escaped_xattr(struct super_block *sb, const char *name)
{
	struct ovl_fs *ofs = sb->s_fs_info;

	if (ofs->config.userxattr)
		return strncmp(name, OVL_XATTR_ESCAPE_USER_PREFIX,
			       OVL_XATTR_ESCAPE_USER_PREFIX_LEN) == 0;
	else
		return strncmp(name, OVL_XATTR_ESCAPE_TRUSTED_PREFIX,
			       OVL_XATTR_ESCAPE_TRUSTED_PREFIX_LEN - 1) == 0;
}

static bool ovl_is_own_xattr(struct super_block *sb, const char *name)
{
	struct ovl_fs *ofs = sb->s_fs_info;

	if (ofs->config.userxattr)
		return strncmp(name, OVL_XATTR_USER_PREFIX,
			       OVL_XATTR_USER_PREFIX_LEN) == 0;
	else
		return strncmp(name, OVL_XATTR_TRUSTED_PREFIX,
			       OVL_XATTR_TRUSTED_PREFIX_LEN) == 0;
}

bool ovl_is_private_xattr(struct super_block *sb, const char *name)
{
	return ovl_is_own_xattr(sb, name) && !ovl_is_escaped_xattr(sb, name);
}

static int ovl_xattr_set(struct dentry *dentry, struct inode *inode, const char *name,
			 const void *value, size_t size, int flags)
{
	int err;
	struct ovl_fs *ofs = OVL_FS(dentry->d_sb);
	struct dentry *upperdentry = ovl_i_dentry_upper(inode);
	struct dentry *realdentry = upperdentry ?: ovl_dentry_lower(dentry);
	struct path realpath;
	const struct cred *old_cred;

	err = ovl_want_write(dentry);
	if (err)
		goto out;

	if (!value && !upperdentry) {
		ovl_path_lower(dentry, &realpath);
		old_cred = ovl_override_creds(dentry->d_sb);
		err = vfs_getxattr(mnt_user_ns(realpath.mnt), realdentry, name, NULL, 0);
		revert_creds(old_cred);
		if (err < 0)
			goto out_drop_write;
	}

	if (!upperdentry) {
		err = ovl_copy_up(dentry);
		if (err)
			goto out_drop_write;

		realdentry = ovl_dentry_upper(dentry);
	}

	old_cred = ovl_override_creds(dentry->d_sb);
	if (value) {
		err = ovl_do_setxattr(ofs, realdentry, name, value, size,
				      flags);
	} else {
		WARN_ON(flags != XATTR_REPLACE);
		err = ovl_do_removexattr(ofs, realdentry, name);
	}
	revert_creds(old_cred);

	/* copy c/mtime */
	ovl_copyattr(inode);

out_drop_write:
	ovl_drop_write(dentry);
out:
	return err;
}

static int ovl_xattr_get(struct dentry *dentry, struct inode *inode, const char *name,
			 void *value, size_t size)
{
	ssize_t res;
	const struct cred *old_cred;
	struct path realpath;

	ovl_i_path_real(inode, &realpath);
	old_cred = ovl_override_creds(dentry->d_sb);
	res = vfs_getxattr(mnt_user_ns(realpath.mnt), realpath.dentry, name, value, size);
	revert_creds(old_cred);
	return res;
}

static bool ovl_can_list(struct super_block *sb, const char *s)
{
	/* Never list private (.overlay) */
	if (ovl_is_private_xattr(sb, s))
		return false;

	/* List all non-trusted xattrs */
	if (strncmp(s, XATTR_TRUSTED_PREFIX, XATTR_TRUSTED_PREFIX_LEN) != 0)
		return true;

	/* list other trusted for superuser only */
	return ns_capable_noaudit(&init_user_ns, CAP_SYS_ADMIN);
}

ssize_t ovl_listxattr(struct dentry *dentry, char *list, size_t size)
{
	struct dentry *realdentry = ovl_dentry_real(dentry);
	struct ovl_fs *ofs = OVL_FS(dentry->d_sb);
	ssize_t res;
	size_t len;
	char *s;
	const struct cred *old_cred;
	size_t prefix_len, name_len;

	old_cred = ovl_override_creds(dentry->d_sb);
	res = vfs_listxattr(realdentry, list, size);
	revert_creds(old_cred);
	if (res <= 0 || size == 0)
		return res;

	prefix_len = ofs->config.userxattr ?
		OVL_XATTR_USER_PREFIX_LEN : OVL_XATTR_TRUSTED_PREFIX_LEN;

	/* filter out private xattrs */
	for (s = list, len = res; len;) {
		size_t slen = strnlen(s, len) + 1;

		/* underlying fs providing us with an broken xattr list? */
		if (WARN_ON(slen > len))
			return -EIO;

		len -= slen;
		if (!ovl_can_list(dentry->d_sb, s)) {
			res -= slen;
			memmove(s, s + slen, len);
		} else if (ovl_is_escaped_xattr(dentry->d_sb, s)) {
			res -= OVL_XATTR_ESCAPE_PREFIX_LEN;
			name_len = slen - prefix_len - OVL_XATTR_ESCAPE_PREFIX_LEN;
			s += prefix_len;
			memmove(s, s + OVL_XATTR_ESCAPE_PREFIX_LEN, name_len + len);
			s += name_len;
		} else {
			s += slen;
		}
	}

	return res;
}

static int __maybe_unused
ovl_posix_acl_xattr_get(const struct xattr_handler *handler,
			struct dentry *dentry, struct inode *inode,
			const char *name, void *buffer, size_t size)
{
	return ovl_xattr_get(dentry, inode, handler->name, buffer, size);
}

static int __maybe_unused
ovl_posix_acl_xattr_set(const struct xattr_handler *handler,
			struct user_namespace *mnt_userns,
			struct dentry *dentry, struct inode *inode,
			const char *name, const void *value,
			size_t size, int flags)
{
	struct dentry *workdir = ovl_workdir(dentry);
	struct inode *realinode = ovl_inode_real(inode);
	struct posix_acl *acl = NULL;
	int err;

	/* Check that everything is OK before copy-up */
	if (value) {
		acl = posix_acl_from_xattr(&init_user_ns, value, size);
		if (IS_ERR(acl))
			return PTR_ERR(acl);
	}
	err = -EOPNOTSUPP;
	if (!IS_POSIXACL(d_inode(workdir)))
		goto out_acl_release;
	if (!realinode->i_op->set_acl)
		goto out_acl_release;
	if (handler->flags == ACL_TYPE_DEFAULT && !S_ISDIR(inode->i_mode)) {
		err = acl ? -EACCES : 0;
		goto out_acl_release;
	}
	err = -EPERM;
	if (!inode_owner_or_capable(&init_user_ns, inode))
		goto out_acl_release;

	posix_acl_release(acl);

	/*
	 * Check if sgid bit needs to be cleared (actual setacl operation will
	 * be done with mounter's capabilities and so that won't do it for us).
	 */
	if (unlikely(inode->i_mode & S_ISGID) &&
	    handler->flags == ACL_TYPE_ACCESS &&
	    !in_group_p(inode->i_gid) &&
	    !capable_wrt_inode_uidgid(&init_user_ns, inode, CAP_FSETID)) {
		struct iattr iattr = { .ia_valid = ATTR_KILL_SGID };

		err = ovl_setattr(&init_user_ns, dentry, &iattr);
		if (err)
			return err;
	}

	err = ovl_xattr_set(dentry, inode, handler->name, value, size, flags);
	return err;

out_acl_release:
	posix_acl_release(acl);
	return err;
}

static char *ovl_xattr_escape_name(const char *prefix, const char *name)
{
	size_t prefix_len = strlen(prefix);
	size_t name_len = strlen(name);
	size_t escaped_len;
	char *escaped, *s;

	escaped_len = prefix_len + OVL_XATTR_ESCAPE_PREFIX_LEN + name_len;
	if (escaped_len > XATTR_NAME_MAX)
		return ERR_PTR(-EOPNOTSUPP);

	escaped = kmalloc(escaped_len + 1, GFP_KERNEL);
	if (escaped == NULL)
		return ERR_PTR(-ENOMEM);

	s = escaped;
	memcpy(s, prefix, prefix_len);
	s += prefix_len;
	memcpy(s, OVL_XATTR_ESCAPE_PREFIX, OVL_XATTR_ESCAPE_PREFIX_LEN);
	s += OVL_XATTR_ESCAPE_PREFIX_LEN;
	memcpy(s, name, name_len + 1);

	return escaped;
}

static int ovl_own_xattr_get(const struct xattr_handler *handler,
			     struct dentry *dentry, struct inode *inode,
			     const char *name, void *buffer, size_t size)
{
	char *escaped;
	int r;

	escaped = ovl_xattr_escape_name(handler->prefix, name);
	if (IS_ERR(escaped))
		return PTR_ERR(escaped);

	r = ovl_xattr_get(dentry, inode, escaped, buffer, size);

	kfree(escaped);

	return r;
}

static int ovl_own_xattr_set(const struct xattr_handler *handler,
			     struct user_namespace *mnt_userns,
			     struct dentry *dentry, struct inode *inode,
			     const char *name, const void *value,
			     size_t size, int flags)
{
	char *escaped;
	int r;

	escaped = ovl_xattr_escape_name(handler->prefix, name);
	if (IS_ERR(escaped))
		return PTR_ERR(escaped);

	r = ovl_xattr_set(dentry, inode, escaped, value, size, flags);

	kfree(escaped);

	return r;
}

static int ovl_other_xattr_get(const struct xattr_handler *handler,
			       struct dentry *dentry, struct inode *inode,
			       const char *name, void *buffer, size_t size)
{
	return ovl_xattr_get(dentry, inode, name, buffer, size);
}

static int ovl_other_xattr_set(const struct xattr_handler *handler,
			       struct user_namespace *mnt_userns,
			       struct dentry *dentry, struct inode *inode,
			       const char *name, const void *value,
			       size_t size, int flags)
{
	return ovl_xattr_set(dentry, inode, name, value, size, flags);
}

static const struct xattr_handler __maybe_unused
ovl_posix_acl_access_xattr_handler = {
	.name = XATTR_NAME_POSIX_ACL_ACCESS,
	.flags = ACL_TYPE_ACCESS,
	.get = ovl_posix_acl_xattr_get,
	.set = ovl_posix_acl_xattr_set,
};

static const struct xattr_handler __maybe_unused
ovl_posix_acl_default_xattr_handler = {
	.name = XATTR_NAME_POSIX_ACL_DEFAULT,
	.flags = ACL_TYPE_DEFAULT,
	.get = ovl_posix_acl_xattr_get,
	.set = ovl_posix_acl_xattr_set,
};

static const struct xattr_handler ovl_own_trusted_xattr_handler = {
	.prefix	= OVL_XATTR_TRUSTED_PREFIX,
	.get = ovl_own_xattr_get,
	.set = ovl_own_xattr_set,
};

static const struct xattr_handler ovl_own_user_xattr_handler = {
	.prefix	= OVL_XATTR_USER_PREFIX,
	.get = ovl_own_xattr_get,
	.set = ovl_own_xattr_set,
};

static const struct xattr_handler ovl_other_xattr_handler = {
	.prefix	= "", /* catch all */
	.get = ovl_other_xattr_get,
	.set = ovl_other_xattr_set,
};

static const struct xattr_handler *ovl_trusted_xattr_handlers[] = {
#ifdef CONFIG_FS_POSIX_ACL
	&ovl_posix_acl_access_xattr_handler,
	&ovl_posix_acl_default_xattr_handler,
#endif
	&ovl_own_trusted_xattr_handler,
	&ovl_other_xattr_handler,
	NULL
};

static const struct xattr_handler *ovl_user_xattr_handlers[] = {
#ifdef CONFIG_FS_POSIX_ACL
	&ovl_posix_acl_access_xattr_handler,
	&ovl_posix_acl_default_xattr_handler,
#endif
	&ovl_own_user_xattr_handler,
	&ovl_other_xattr_handler,
	NULL
};

const struct xattr_handler **ovl_xattr_handlers(struct ovl_fs *ofs)
{
	return ofs->config.userxattr ? ovl_user_xattr_handlers :
		ovl_trusted_xattr_handlers;
}

