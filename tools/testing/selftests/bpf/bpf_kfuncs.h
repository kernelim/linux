#ifndef __BPF_KFUNCS__
#define __BPF_KFUNCS__

/* Description
 *  Initializes an skb-type dynptr
 * Returns
 *  Error code
 */
extern int bpf_dynptr_from_skb(struct __sk_buff *skb, __u64 flags,
    struct bpf_dynptr *ptr__uninit) __ksym __weak;

/* Description
 *  Initializes an xdp-type dynptr
 * Returns
 *  Error code
 */
extern int bpf_dynptr_from_xdp(struct xdp_md *xdp, __u64 flags,
			       struct bpf_dynptr *ptr__uninit) __ksym __weak;

/* Description
 *  Obtain a read-only pointer to the dynptr's data
 * Returns
 *  Either a direct pointer to the dynptr data or a pointer to the user-provided
 *  buffer if unable to obtain a direct pointer
 */
extern void *bpf_dynptr_slice(const struct bpf_dynptr *ptr, __u32 offset,
			      void *buffer, __u32 buffer__szk) __ksym __weak;

/* Description
 *  Obtain a read-write pointer to the dynptr's data
 * Returns
 *  Either a direct pointer to the dynptr data or a pointer to the user-provided
 *  buffer if unable to obtain a direct pointer
 */
extern void *bpf_dynptr_slice_rdwr(const struct bpf_dynptr *ptr, __u32 offset,
			      void *buffer, __u32 buffer__szk) __ksym __weak;

extern int bpf_dynptr_adjust(const struct bpf_dynptr *ptr, __u32 start, __u32 end) __ksym __weak;
extern bool bpf_dynptr_is_null(const struct bpf_dynptr *ptr) __ksym __weak;
extern bool bpf_dynptr_is_rdonly(const struct bpf_dynptr *ptr) __ksym __weak;
extern __u32 bpf_dynptr_size(const struct bpf_dynptr *ptr) __ksym __weak;
extern int bpf_dynptr_clone(const struct bpf_dynptr *ptr, struct bpf_dynptr *clone__init) __ksym __weak;

void *bpf_cast_to_kern_ctx(void *) __ksym;

extern void *bpf_rdonly_cast(const void *obj, __u32 btf_id) __ksym __weak;

extern int bpf_get_file_xattr(struct file *file, const char *name,
			      struct bpf_dynptr *value_ptr) __ksym;
extern int bpf_get_fsverity_digest(struct file *file, struct bpf_dynptr *digest_ptr) __ksym;

extern struct bpf_key *bpf_lookup_user_key(__u32 serial, __u64 flags) __ksym;
extern struct bpf_key *bpf_lookup_system_key(__u64 id) __ksym;
extern void bpf_key_put(struct bpf_key *key) __ksym;
extern int bpf_verify_pkcs7_signature(struct bpf_dynptr *data_ptr,
				      struct bpf_dynptr *sig_ptr,
				      struct bpf_key *trusted_keyring) __ksym;

extern bool bpf_session_is_return(void) __ksym __weak;
extern __u64 *bpf_session_cookie(void) __ksym __weak;

struct dentry;
/* Description
 *  Returns xattr of a dentry
 * Returns
 *  Error code
 */
extern int bpf_get_dentry_xattr(struct dentry *dentry, const char *name,
			      struct bpf_dynptr *value_ptr) __ksym __weak;
#endif
