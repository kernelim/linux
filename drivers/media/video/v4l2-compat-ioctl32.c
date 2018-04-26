/*
 * ioctl32.c: Conversion between 32bit and 64bit native ioctls.
 *	Separated from fs stuff by Arnd Bergmann <arnd@arndb.de>
 *
 * Copyright (C) 1997-2000  Jakub Jelinek  (jakub@redhat.com)
 * Copyright (C) 1998  Eddie C. Dost  (ecd@skynet.be)
 * Copyright (C) 2001,2002  Andi Kleen, SuSE Labs
 * Copyright (C) 2003       Pavel Machek (pavel@ucw.cz)
 * Copyright (C) 2005       Philippe De Muyter (phdm@macqel.be)
 * Copyright (C) 2008       Hans Verkuil <hverkuil@xs4all.nl>
 *
 * These routines maintain argument size conversion between 32bit and 64bit
 * ioctls.
 */

#include <linux/compat.h>
#define __OLD_VIDIOC_ /* To allow fixing old calls*/
#include <linux/videodev2.h>
#include <linux/module.h>
#include <media/v4l2-ioctl.h>

/* Use the same argument order as copy_in_user */
#define assign_in_user(to, from)					\
({									\
	typeof(*from) __assign_tmp;					\
									\
	get_user(__assign_tmp, from) || put_user(__assign_tmp, to);	\
})

#ifdef CONFIG_COMPAT

static long native_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	long ret = -ENOIOCTLCMD;

	if (file->f_op->unlocked_ioctl)
		ret = file->f_op->unlocked_ioctl(file, cmd, arg);

	return ret;
}


struct v4l2_clip32 {
	struct v4l2_rect        c;
	compat_caddr_t 		next;
};

struct v4l2_window32 {
	struct v4l2_rect        w;
	enum v4l2_field  	field;
	__u32			chromakey;
	compat_caddr_t		clips; /* actually struct v4l2_clip32 * */
	__u32			clipcount;
	compat_caddr_t		bitmap;
};

static int get_v4l2_window32(struct v4l2_window __user *kp,
			     struct v4l2_window32 __user *up,
			     void __user *aux_buf, u32 aux_space)
{
	u32 clipcount;

	if (!access_ok(VERIFY_READ, up, sizeof(struct v4l2_window32)) ||
	    copy_in_user(&kp->w, &up->w, sizeof(up->w)) ||
	    assign_in_user(&kp->field, &up->field) ||
	    assign_in_user(&kp->chromakey, &up->chromakey) ||
	    get_user(clipcount, &up->clipcount) ||
	    put_user(clipcount, &kp->clipcount))
		return -EFAULT;
	if (clipcount > 2048)
		return -EINVAL;
	if (clipcount) {
		struct v4l2_clip32 __user *uclips;
		struct v4l2_clip __user *kclips;
		compat_caddr_t p;

		if (get_user(p, &up->clips))
			return -EFAULT;
		uclips = compat_ptr(p);
		if (aux_space < clipcount * sizeof(*kclips))
			return -EFAULT;
		kclips = aux_buf;
		if (put_user(kclips, &kp->clips))
			return -EFAULT;

		while (--clipcount >= 0) {
			if (copy_in_user(&kclips->c, &uclips->c, sizeof(uclips->c)))
				return -EFAULT;
			if (put_user(clipcount ? kclips + 1 : NULL, &kclips->next))
				return -EFAULT;
			uclips += 1;
			kclips += 1;
		}
	} else
		return put_user(NULL, &kp->clips);
	return 0;
}

static int put_v4l2_window32(struct v4l2_window __user *kp,
			     struct v4l2_window32 __user *up)
{
	u32 clipcount;

	if (copy_in_user(&up->w, &kp->w, sizeof(kp->w)) ||
	    assign_in_user(&up->field, &kp->field) ||
	    assign_in_user(&up->chromakey, &kp->chromakey) ||
	    get_user(clipcount, &kp->clipcount) ||
	    put_user(clipcount, &up->clipcount))
		return -EFAULT;
	return 0;
}

static inline int get_v4l2_pix_format(struct v4l2_pix_format __user *kp,
				      struct v4l2_pix_format __user *up)
{
	if (copy_in_user(kp, up, sizeof(struct v4l2_pix_format)))
		return -EFAULT;
	return 0;
}

static inline int put_v4l2_pix_format(struct v4l2_pix_format __user *kp,
				      struct v4l2_pix_format __user *up)
{
	if (copy_in_user(up, kp, sizeof(struct v4l2_pix_format)))
		return -EFAULT;
	return 0;
}

static inline int get_v4l2_vbi_format(struct v4l2_vbi_format __user *kp,
				      struct v4l2_vbi_format __user *up)
{
	if (copy_in_user(kp, up, sizeof(struct v4l2_vbi_format)))
		return -EFAULT;
	return 0;
}

static inline int put_v4l2_vbi_format(struct v4l2_vbi_format __user *kp,
				      struct v4l2_vbi_format __user *up)
{
	if (copy_in_user(up, kp, sizeof(struct v4l2_vbi_format)))
		return -EFAULT;
	return 0;
}

static inline int get_v4l2_sliced_vbi_format(struct v4l2_sliced_vbi_format __user *kp,
					     struct v4l2_sliced_vbi_format __user *up)
{
	if (copy_in_user(kp, up, sizeof(struct v4l2_sliced_vbi_format)))
		return -EFAULT;
	return 0;
}

static inline int put_v4l2_sliced_vbi_format(struct v4l2_sliced_vbi_format __user *kp,
					     struct v4l2_sliced_vbi_format __user *up)
{
	if (copy_in_user(up, kp, sizeof(struct v4l2_sliced_vbi_format)))
		return -EFAULT;
	return 0;
}

struct v4l2_format32 {
	enum v4l2_buf_type type;
	union {
		struct v4l2_pix_format	pix;
		struct v4l2_window32	win;
		struct v4l2_vbi_format	vbi;
		struct v4l2_sliced_vbi_format	sliced;
		__u8	raw_data[200];        /* user-defined */
	} fmt;
};

static int __bufsize_v4l2_format(struct v4l2_format32 __user *up, u32 *size)
{
	u32 type;

	if (get_user(type, &up->type))
		return -EFAULT;

	switch (type) {
	case V4L2_BUF_TYPE_VIDEO_OVERLAY:
	case V4L2_BUF_TYPE_VIDEO_OUTPUT_OVERLAY: {
		u32 clipcount;

		if (get_user(clipcount, &up->fmt.win.clipcount))
			return -EFAULT;
		if (clipcount > 2048)
			return -EINVAL;
		*size = clipcount * sizeof(struct v4l2_clip);
		return 0;
	}
	default:
		*size = 0;
		return 0;
	}
}

static int bufsize_v4l2_format(struct v4l2_format32 __user *up, u32 *size)
{
	if (!access_ok(VERIFY_READ, up, sizeof(*up)))
		return -EFAULT;
	return __bufsize_v4l2_format(up, size);
}

static int get_v4l2_format32(struct v4l2_format __user *kp,
			     struct v4l2_format32 __user *up,
			     void __user *aux_buf, u32 aux_space)
{
	u32 type;

	if (!access_ok(VERIFY_READ, up, sizeof(struct v4l2_format32)) ||
	    get_user(type, &up->type) || put_user(type, &kp->type))
		return -EFAULT;

	switch (type) {
	case V4L2_BUF_TYPE_VIDEO_CAPTURE:
	case V4L2_BUF_TYPE_VIDEO_OUTPUT:
		return get_v4l2_pix_format(&kp->fmt.pix, &up->fmt.pix);
	case V4L2_BUF_TYPE_VIDEO_OVERLAY:
	case V4L2_BUF_TYPE_VIDEO_OUTPUT_OVERLAY:
		return get_v4l2_window32(&kp->fmt.win, &up->fmt.win,
					 aux_buf, aux_space);
	case V4L2_BUF_TYPE_VBI_CAPTURE:
	case V4L2_BUF_TYPE_VBI_OUTPUT:
		return get_v4l2_vbi_format(&kp->fmt.vbi, &up->fmt.vbi);
	case V4L2_BUF_TYPE_SLICED_VBI_CAPTURE:
	case V4L2_BUF_TYPE_SLICED_VBI_OUTPUT:
		return get_v4l2_sliced_vbi_format(&kp->fmt.sliced, &up->fmt.sliced);
	case V4L2_BUF_TYPE_PRIVATE:
		if (copy_in_user(kp, up, sizeof(kp->fmt.raw_data)))
			return -EFAULT;
		return 0;
	default:
		printk(KERN_INFO "compat_ioctl32: unexpected VIDIOC_FMT type %d\n",
								kp->type);
		return -EINVAL;
	}
}

static int put_v4l2_format32(struct v4l2_format __user *kp,
			     struct v4l2_format32 __user *up)
{
	u32 type;

	if (!access_ok(VERIFY_WRITE, up, sizeof(struct v4l2_format32)) ||
		get_user(type, &kp->type))
		return -EFAULT;
	switch (type) {
	case V4L2_BUF_TYPE_VIDEO_CAPTURE:
	case V4L2_BUF_TYPE_VIDEO_OUTPUT:
		return put_v4l2_pix_format(&kp->fmt.pix, &up->fmt.pix);
	case V4L2_BUF_TYPE_VIDEO_OVERLAY:
	case V4L2_BUF_TYPE_VIDEO_OUTPUT_OVERLAY:
		return put_v4l2_window32(&kp->fmt.win, &up->fmt.win);
	case V4L2_BUF_TYPE_VBI_CAPTURE:
	case V4L2_BUF_TYPE_VBI_OUTPUT:
		return put_v4l2_vbi_format(&kp->fmt.vbi, &up->fmt.vbi);
	case V4L2_BUF_TYPE_SLICED_VBI_CAPTURE:
	case V4L2_BUF_TYPE_SLICED_VBI_OUTPUT:
		return put_v4l2_sliced_vbi_format(&kp->fmt.sliced, &up->fmt.sliced);
	case V4L2_BUF_TYPE_PRIVATE:
		if (copy_to_user(up, kp, sizeof(up->fmt.raw_data)))
			return -EFAULT;
		return 0;
	default:
		printk(KERN_INFO "compat_ioctl32: unexpected VIDIOC_FMT type %d\n",
								kp->type);
		return -EINVAL;
	}
}

struct v4l2_standard32 {
	__u32		     index;
	compat_u64	     id;
	__u8		     name[24];
	struct v4l2_fract    frameperiod; /* Frames, not fields */
	__u32		     framelines;
	__u32		     reserved[4];
};

static int get_v4l2_standard32(struct v4l2_standard __user *kp,
			       struct v4l2_standard32 __user *up)
{
	/* other fields are not set by the user, nor used by the driver */
	if (!access_ok(VERIFY_READ, up, sizeof(struct v4l2_standard32)) ||
	    assign_in_user(&kp->index, &up->index))
		return -EFAULT;
	return 0;
}

static int put_v4l2_standard32(struct v4l2_standard __user *kp,
			       struct v4l2_standard32 __user *up)
{
	if (!access_ok(VERIFY_WRITE, up, sizeof(struct v4l2_standard32)) ||
	    assign_in_user(&up->index, &kp->index) ||
	    assign_in_user(&up->id, &kp->id) ||
	    copy_in_user(up->name, kp->name, sizeof(up->name)) ||
	    copy_in_user(&up->frameperiod, &kp->frameperiod,
			 sizeof(up->frameperiod)) ||
	    assign_in_user(&up->framelines, &kp->framelines) ||
	    copy_in_user(up->reserved, kp->reserved, sizeof(up->reserved)))
		return -EFAULT;
	return 0;
}

struct v4l2_buffer32 {
	__u32			index;
	enum v4l2_buf_type      type;
	__u32			bytesused;
	__u32			flags;
	enum v4l2_field		field;
	struct compat_timeval	timestamp;
	struct v4l2_timecode	timecode;
	__u32			sequence;

	/* memory location */
	enum v4l2_memory        memory;
	union {
		__u32           offset;
		compat_long_t   userptr;
	} m;
	__u32			length;
	__u32			input;
	__u32			reserved;
};

static int get_v4l2_buffer32(struct v4l2_buffer __user *kp,
			     struct v4l2_buffer32 __user *up,
			     void __user *aux_buf, u32 aux_space)
{
	u32 type;
	u32 length;
	enum v4l2_memory memory;

	if (!access_ok(VERIFY_READ, up, sizeof(struct v4l2_buffer32)) ||
	    assign_in_user(&kp->index, &up->index) ||
	    get_user(type, &up->type) ||
	    put_user(type, &kp->type) ||
	    assign_in_user(&kp->flags, &up->flags) ||
	    get_user(memory, &up->memory) ||
	    put_user(memory, &kp->memory) ||
	    get_user(length, &up->length) ||
	    put_user(length, &kp->length) ||
	    assign_in_user(&kp->input, &up->input))
		return -EFAULT;

	switch (memory) {
	case V4L2_MEMORY_MMAP:
		if (assign_in_user(&kp->m.offset, &up->m.offset))
			return -EFAULT;
		break;
	case V4L2_MEMORY_USERPTR:
		{
		compat_ulong_t userptr;

		if (get_user(userptr, &up->m.userptr) ||
		    put_user((unsigned long)compat_ptr(userptr),
			     &kp->m.userptr))
			return -EFAULT;

		}
		break;
	case V4L2_MEMORY_OVERLAY:
		if (assign_in_user(&kp->m.offset, &up->m.offset))
			return -EFAULT;
		break;
	}
	return 0;
}

static int put_v4l2_buffer32(struct v4l2_buffer __user *kp,
			     struct v4l2_buffer32 __user *up)
{
	u32 type;
	u32 length;
	enum v4l2_memory memory;

	if (!access_ok(VERIFY_WRITE, up, sizeof(struct v4l2_buffer32)) ||
	    assign_in_user(&up->index, &kp->index) ||
	    get_user(type, &kp->type) ||
	    put_user(type, &up->type) ||
	    assign_in_user(&up->flags, &kp->flags) ||
	    assign_in_user(&up->input, &kp->input) ||
	    get_user(memory, &kp->memory) ||
	    put_user(memory, &up->memory))
		return -EFAULT;

	switch (memory) {
	case V4L2_MEMORY_MMAP:
		if (assign_in_user(&up->m.offset, &kp->m.offset))
			return -EFAULT;
		break;
	case V4L2_MEMORY_USERPTR:
		if (assign_in_user(&up->m.userptr, &kp->m.userptr))
			return -EFAULT;
		break;
	case V4L2_MEMORY_OVERLAY:
		if (assign_in_user(&up->m.offset, &kp->m.offset))
			return -EFAULT;
		break;
	}
	if (assign_in_user(&up->bytesused, &kp->bytesused) ||
	    assign_in_user(&up->field, &kp->field) ||
	    assign_in_user(&up->timestamp.tv_sec, &kp->timestamp.tv_sec) ||
	    assign_in_user(&up->timestamp.tv_usec, &kp->timestamp.tv_usec) ||
	    copy_in_user(&up->timecode, &kp->timecode, sizeof(kp->timecode)) ||
	    assign_in_user(&up->sequence, &kp->sequence) ||
	    assign_in_user(&up->reserved, &kp->reserved) ||
	    get_user(length, &kp->length) ||
	    put_user(length, &up->length))
		return -EFAULT;
	return 0;
}

struct v4l2_framebuffer32 {
	__u32			capability;
	__u32			flags;
	compat_caddr_t 		base;
	struct v4l2_pix_format	fmt;
};

static int get_v4l2_framebuffer32(struct v4l2_framebuffer __user *kp,
				  struct v4l2_framebuffer32 __user *up)
{
	compat_caddr_t tmp;

	if (!access_ok(VERIFY_READ, up, sizeof(struct v4l2_framebuffer32)) ||
	    get_user(tmp, &up->base) ||
	    put_user((__force void *)compat_ptr(tmp), &kp->base) ||
	    assign_in_user(&kp->capability, &up->capability) ||
	    assign_in_user(&kp->flags, &up->flags) ||
	    copy_in_user(&kp->fmt, &up->fmt, sizeof(kp->fmt)))
		return -EFAULT;
	return 0;
}

static int put_v4l2_framebuffer32(struct v4l2_framebuffer __user *kp,
				  struct v4l2_framebuffer32 __user *up)
{
	void *base;

	if (!access_ok(VERIFY_WRITE, up, sizeof(struct v4l2_framebuffer32)) ||
	    get_user(base, &kp->base) ||
	    put_user(ptr_to_compat(base), &up->base) ||
	    assign_in_user(&up->capability, &kp->capability) ||
	    assign_in_user(&up->flags, &kp->flags) ||
	    copy_in_user(&up->fmt, &kp->fmt, sizeof(kp->fmt)))
		return -EFAULT;
	return 0;
}

struct v4l2_input32 {
	__u32	     index;		/*  Which input */
	__u8	     name[32];		/*  Label */
	__u32	     type;		/*  Type of input */
	__u32	     audioset;		/*  Associated audios (bitfield) */
	__u32        tuner;             /*  Associated tuner */
	v4l2_std_id  std;
	__u32	     status;
	__u32	     reserved[4];
} __attribute__ ((packed));

/*
 * The 64-bit v4l2_input struct has extra padding at the end of the struct.
 * Otherwise it is identical to the 32-bit version.
 */
static inline int get_v4l2_input32(struct v4l2_input __user *kp,
				   struct v4l2_input32 __user *up)
{
	if (copy_in_user(kp, up, sizeof(struct v4l2_input32)))
		return -EFAULT;
	return 0;
}

static inline int put_v4l2_input32(struct v4l2_input __user *kp,
				   struct v4l2_input32 __user *up)
{
	if (copy_in_user(up, kp, sizeof(struct v4l2_input32)))
		return -EFAULT;
	return 0;
}

struct v4l2_ext_controls32 {
       __u32 ctrl_class;
       __u32 count;
       __u32 error_idx;
       __u32 reserved[2];
       compat_caddr_t controls; /* actually struct v4l2_ext_control32 * */
};

struct v4l2_ext_control32 {
	__u32 id;
	__u32 size;
	__u32 reserved2[1];
	union {
		__s32 value;
		__s64 value64;
		compat_caddr_t string; /* actually char * */
	};
} __attribute__ ((packed));

/* The following function really belong in v4l2-common, but that causes
   a circular dependency between modules. We need to think about this, but
   for now this will do. */

/* Return non-zero if this control is a pointer type. Currently only
   type STRING is a pointer type. */
static inline int ctrl_is_pointer(u32 id)
{
	switch (id) {
	case V4L2_CID_RDS_TX_PS_NAME:
	case V4L2_CID_RDS_TX_RADIO_TEXT:
		return 1;
	default:
		return 0;
	}
}

static int bufsize_v4l2_ext_controls(struct v4l2_ext_controls32 __user *up,
				      u32 *size)
{
	u32 count;

	if (!access_ok(VERIFY_READ, up, sizeof(*up)) ||
	    get_user(count, &up->count))
		return -EFAULT;
	*size = count * sizeof(struct v4l2_ext_control);
	return 0;
}

static int get_v4l2_ext_controls32(struct v4l2_ext_controls __user *kp,
				   struct v4l2_ext_controls32 __user *up,
				   void __user *aux_buf, u32 aux_space)
{
	struct v4l2_ext_control32 __user *ucontrols;
	struct v4l2_ext_control __user *kcontrols;
	u32 count;
	u32 n;
	compat_caddr_t p;

	if (!access_ok(VERIFY_READ, up, sizeof(struct v4l2_ext_controls32)) ||
	    assign_in_user(&kp->ctrl_class, &up->ctrl_class) ||
	    get_user(count, &up->count) ||
	    put_user(count, &kp->count) ||
	    assign_in_user(&kp->error_idx, &up->error_idx) ||
	    copy_in_user(kp->reserved, up->reserved, sizeof(kp->reserved)))
		return -EFAULT;

	if (count == 0)
		return put_user(NULL, &kp->controls);
	if (get_user(p, &up->controls))
		return -EFAULT;
	ucontrols = compat_ptr(p);
	if (!access_ok(VERIFY_READ, ucontrols,
		       count * sizeof(struct v4l2_ext_control)))
		return -EFAULT;
	if (aux_space < count * sizeof(*kcontrols))
		return -EFAULT;
	kcontrols = aux_buf;
	if (put_user((__force struct v4l2_ext_control *)kcontrols,
		     &kp->controls))
		return -EFAULT;

	for (n = 0; n < count; n++) {
		u32 id;

		if (copy_in_user(kcontrols, ucontrols, sizeof(*kcontrols)))
			return -EFAULT;

		if (get_user(id, &kcontrols->id))
			return -EFAULT;

		if (ctrl_is_pointer(id)) {
			void __user *s;

			if (get_user(p, &ucontrols->string))
				return -EFAULT;
			s = compat_ptr(p);
			if (put_user(s, &kcontrols->string))
				return -EFAULT;
		}
		ucontrols++;
		kcontrols++;
	}
	return 0;
}

static int put_v4l2_ext_controls32(struct v4l2_ext_controls __user *kp,
				   struct v4l2_ext_controls32 __user *up)
{
	struct v4l2_ext_control32 __user *ucontrols;
	struct v4l2_ext_control __user *kcontrols;
	u32 count;
	u32 n;
	compat_caddr_t p;

	if (!access_ok(VERIFY_WRITE, up, sizeof(struct v4l2_ext_controls32)) ||
	    assign_in_user(&up->ctrl_class, &kp->ctrl_class) ||
	    get_user(count, &kp->count) ||
	    put_user(count, &up->count) ||
	    assign_in_user(&up->error_idx, &kp->error_idx) ||
	    copy_in_user(up->reserved, kp->reserved, sizeof(up->reserved)) ||
	    get_user(kcontrols, &kp->controls))
		return -EFAULT;

	if (!count)
		return 0;
	if (get_user(p, &up->controls))
		return -EFAULT;
	ucontrols = compat_ptr(p);
	if (!access_ok(VERIFY_WRITE, ucontrols,
		       count * sizeof(struct v4l2_ext_control)))
		return -EFAULT;

	for (n = 0; n < count; n++) {
		unsigned int size = sizeof(*ucontrols);
		u32 id;

		if (get_user(id, &kcontrols->id) ||
		    put_user(id, &ucontrols->id) ||
		    assign_in_user(&ucontrols->size, &kcontrols->size) ||
		    copy_in_user(&ucontrols->reserved2, &kcontrols->reserved2,
				 sizeof(ucontrols->reserved2)))
			return -EFAULT;

		/*
		 * Do not modify the pointer when copying a pointer control.
		 * The contents of the pointer was changed, not the pointer
		 * itself.
		 */
		if (ctrl_is_pointer(id))
			size -= sizeof(ucontrols->value64);

		if (copy_in_user(ucontrols, kcontrols, size))
			return -EFAULT;

		ucontrols++;
		kcontrols++;
	}
	return 0;
}

#define VIDIOC_G_FMT32		_IOWR('V',  4, struct v4l2_format32)
#define VIDIOC_S_FMT32		_IOWR('V',  5, struct v4l2_format32)
#define VIDIOC_QUERYBUF32	_IOWR('V',  9, struct v4l2_buffer32)
#define VIDIOC_G_FBUF32		_IOR ('V', 10, struct v4l2_framebuffer32)
#define VIDIOC_S_FBUF32		_IOW ('V', 11, struct v4l2_framebuffer32)
#define VIDIOC_QBUF32		_IOWR('V', 15, struct v4l2_buffer32)
#define VIDIOC_DQBUF32		_IOWR('V', 17, struct v4l2_buffer32)
#define VIDIOC_ENUMSTD32	_IOWR('V', 25, struct v4l2_standard32)
#define VIDIOC_ENUMINPUT32	_IOWR('V', 26, struct v4l2_input32)
#define VIDIOC_TRY_FMT32      	_IOWR('V', 64, struct v4l2_format32)
#define VIDIOC_G_EXT_CTRLS32    _IOWR('V', 71, struct v4l2_ext_controls32)
#define VIDIOC_S_EXT_CTRLS32    _IOWR('V', 72, struct v4l2_ext_controls32)
#define VIDIOC_TRY_EXT_CTRLS32  _IOWR('V', 73, struct v4l2_ext_controls32)

#define VIDIOC_OVERLAY32	_IOW ('V', 14, s32)
#ifdef __OLD_VIDIOC_
#define VIDIOC_OVERLAY32_OLD	_IOWR('V', 14, s32)
#endif
#define VIDIOC_STREAMON32	_IOW ('V', 18, s32)
#define VIDIOC_STREAMOFF32	_IOW ('V', 19, s32)
#define VIDIOC_G_INPUT32	_IOR ('V', 38, s32)
#define VIDIOC_S_INPUT32	_IOWR('V', 39, s32)
#define VIDIOC_G_OUTPUT32	_IOR ('V', 46, s32)
#define VIDIOC_S_OUTPUT32	_IOWR('V', 47, s32)

static int alloc_userspace(unsigned int size, u32 aux_space,
			    void __user **up_native)
{
	*up_native = compat_alloc_user_space(size + aux_space);
	if (!*up_native)
		return -ENOMEM;
	if (clear_user(*up_native, size))
		return -EFAULT;
	return 0;
}

static long do_video_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	void __user *up = compat_ptr(arg);
	void __user *up_native = NULL;
	void __user *aux_buf;
	u32 aux_space;
	int compatible_arg = 1;
	long err = 0;

	/* First, convert the command. */
	switch (cmd) {
	case VIDIOC_G_FMT32: cmd = VIDIOC_G_FMT; break;
	case VIDIOC_S_FMT32: cmd = VIDIOC_S_FMT; break;
	case VIDIOC_QUERYBUF32: cmd = VIDIOC_QUERYBUF; break;
	case VIDIOC_G_FBUF32: cmd = VIDIOC_G_FBUF; break;
	case VIDIOC_S_FBUF32: cmd = VIDIOC_S_FBUF; break;
	case VIDIOC_QBUF32: cmd = VIDIOC_QBUF; break;
	case VIDIOC_DQBUF32: cmd = VIDIOC_DQBUF; break;
	case VIDIOC_ENUMSTD32: cmd = VIDIOC_ENUMSTD; break;
	case VIDIOC_ENUMINPUT32: cmd = VIDIOC_ENUMINPUT; break;
	case VIDIOC_TRY_FMT32: cmd = VIDIOC_TRY_FMT; break;
	case VIDIOC_G_EXT_CTRLS32: cmd = VIDIOC_G_EXT_CTRLS; break;
	case VIDIOC_S_EXT_CTRLS32: cmd = VIDIOC_S_EXT_CTRLS; break;
	case VIDIOC_TRY_EXT_CTRLS32: cmd = VIDIOC_TRY_EXT_CTRLS; break;
	case VIDIOC_OVERLAY32: cmd = VIDIOC_OVERLAY; break;
#ifdef __OLD_VIDIOC_
	case VIDIOC_OVERLAY32_OLD: cmd = VIDIOC_OVERLAY; break;
#endif
	case VIDIOC_STREAMON32: cmd = VIDIOC_STREAMON; break;
	case VIDIOC_STREAMOFF32: cmd = VIDIOC_STREAMOFF; break;
	case VIDIOC_G_INPUT32: cmd = VIDIOC_G_INPUT; break;
	case VIDIOC_S_INPUT32: cmd = VIDIOC_S_INPUT; break;
	case VIDIOC_G_OUTPUT32: cmd = VIDIOC_G_OUTPUT; break;
	case VIDIOC_S_OUTPUT32: cmd = VIDIOC_S_OUTPUT; break;
	}

	switch (cmd) {
	case VIDIOC_OVERLAY:
	case VIDIOC_STREAMON:
	case VIDIOC_STREAMOFF:
	case VIDIOC_S_INPUT:
	case VIDIOC_S_OUTPUT:
		err = alloc_userspace(sizeof(unsigned int), 0, &up_native);
		if (!err && assign_in_user((unsigned int __user *)up_native,
					   (compat_uint_t __user *)up))
			err = -EFAULT;
		compatible_arg = 0;
		break;

	case VIDIOC_G_INPUT:
	case VIDIOC_G_OUTPUT:
		err = alloc_userspace(sizeof(unsigned int), 0, &up_native);
		compatible_arg = 0;
		break;

	case VIDIOC_G_FMT:
	case VIDIOC_S_FMT:
	case VIDIOC_TRY_FMT:
		err = bufsize_v4l2_format(up, &aux_space);
		if (!err)
			err = alloc_userspace(sizeof(struct v4l2_format),
					      aux_space, &up_native);
		if (!err) {
			aux_buf = up_native + sizeof(struct v4l2_format);
			err = get_v4l2_format32(up_native, up,
						aux_buf, aux_space);
		}
		compatible_arg = 0;
		break;

	case VIDIOC_QUERYBUF:
	case VIDIOC_QBUF:
	case VIDIOC_DQBUF:
		err = alloc_userspace(sizeof(struct v4l2_buffer), 0,
				      &up_native);
		if (!err) {
			aux_buf = up_native + sizeof(struct v4l2_buffer);
			err = get_v4l2_buffer32(up_native, up,
						aux_buf, 0);
		}
		compatible_arg = 0;
		break;

	case VIDIOC_S_FBUF:
		err = alloc_userspace(sizeof(struct v4l2_framebuffer), 0,
				      &up_native);
		if (!err)
			err = get_v4l2_framebuffer32(up_native, up);
		compatible_arg = 0;
		break;

	case VIDIOC_G_FBUF:
		err = alloc_userspace(sizeof(struct v4l2_framebuffer), 0,
				      &up_native);
		compatible_arg = 0;
		break;

	case VIDIOC_ENUMSTD:
		err = alloc_userspace(sizeof(struct v4l2_standard), 0,
				      &up_native);
		if (!err)
			err = get_v4l2_standard32(up_native, up);
		compatible_arg = 0;
		break;

	case VIDIOC_ENUMINPUT:
		err = alloc_userspace(sizeof(struct v4l2_input), 0, &up_native);
		if (!err)
			err = get_v4l2_input32(up_native, up);
		compatible_arg = 0;
		break;

	case VIDIOC_G_EXT_CTRLS:
	case VIDIOC_S_EXT_CTRLS:
	case VIDIOC_TRY_EXT_CTRLS:
		err = bufsize_v4l2_ext_controls(up, &aux_space);
		if (!err)
			err = alloc_userspace(sizeof(struct v4l2_ext_controls),
					      aux_space, &up_native);
		if (!err) {
			aux_buf = up_native + sizeof(struct v4l2_ext_controls);
			err = get_v4l2_ext_controls32(up_native, up,
						      aux_buf, aux_space);
		}
		compatible_arg = 0;
		break;
	}
	if (err)
		return err;

	if (compatible_arg)
		err = native_ioctl(file, cmd, (unsigned long)up);
	else
		err = native_ioctl(file, cmd, (unsigned long)up_native);

	if (err == -ENOTTY)
		return err;

	/*
	 * Special case: even after an error we need to put the
	 * results back for these ioctls since the error_idx will
	 * contain information on which control failed.
	 */
	switch (cmd) {
	case VIDIOC_G_EXT_CTRLS:
	case VIDIOC_S_EXT_CTRLS:
	case VIDIOC_TRY_EXT_CTRLS:
		if (put_v4l2_ext_controls32(up_native, up))
			err = -EFAULT;
		break;
	}
	if (err)
		return err;

	switch (cmd) {
	case VIDIOC_S_INPUT:
	case VIDIOC_S_OUTPUT:
	case VIDIOC_G_INPUT:
	case VIDIOC_G_OUTPUT:
		if (assign_in_user((compat_uint_t __user *)up,
				   ((unsigned int __user *)up_native)))
			err = -EFAULT;
		break;

	case VIDIOC_G_FBUF:
		err = put_v4l2_framebuffer32(up_native, up);
		break;

	case VIDIOC_G_FMT:
	case VIDIOC_S_FMT:
	case VIDIOC_TRY_FMT:
		err = put_v4l2_format32(up_native, up);
		break;

	case VIDIOC_QUERYBUF:
	case VIDIOC_QBUF:
	case VIDIOC_DQBUF:
		err = put_v4l2_buffer32(up_native, up);
		break;

	case VIDIOC_ENUMSTD:
		err = put_v4l2_standard32(up_native, up);
		break;

	case VIDIOC_ENUMINPUT:
		err = put_v4l2_input32(up_native, up);
		break;
	}
	return err;
}

long v4l2_compat_ioctl32(struct file *file, unsigned int cmd, unsigned long arg)
{
	long ret = -ENOIOCTLCMD;

	if (!file->f_op->unlocked_ioctl)
		return ret;

	switch (cmd) {
#ifdef __OLD_VIDIOC_
	case VIDIOC_OVERLAY32_OLD:
	case VIDIOC_S_PARM_OLD:
	case VIDIOC_S_CTRL_OLD:
	case VIDIOC_G_AUDIO_OLD:
	case VIDIOC_G_AUDOUT_OLD:
	case VIDIOC_CROPCAP_OLD:
#endif
	case VIDIOC_QUERYCAP:
	case VIDIOC_RESERVED:
	case VIDIOC_ENUM_FMT:
	case VIDIOC_G_FMT32:
	case VIDIOC_S_FMT32:
	case VIDIOC_REQBUFS:
	case VIDIOC_QUERYBUF32:
	case VIDIOC_G_FBUF32:
	case VIDIOC_S_FBUF32:
	case VIDIOC_OVERLAY32:
	case VIDIOC_QBUF32:
	case VIDIOC_DQBUF32:
	case VIDIOC_STREAMON32:
	case VIDIOC_STREAMOFF32:
	case VIDIOC_G_PARM:
	case VIDIOC_S_PARM:
	case VIDIOC_G_STD:
	case VIDIOC_S_STD:
	case VIDIOC_ENUMSTD32:
	case VIDIOC_ENUMINPUT32:
	case VIDIOC_G_CTRL:
	case VIDIOC_S_CTRL:
	case VIDIOC_G_TUNER:
	case VIDIOC_S_TUNER:
	case VIDIOC_G_AUDIO:
	case VIDIOC_S_AUDIO:
	case VIDIOC_QUERYCTRL:
	case VIDIOC_QUERYMENU:
	case VIDIOC_G_INPUT32:
	case VIDIOC_S_INPUT32:
	case VIDIOC_G_OUTPUT32:
	case VIDIOC_S_OUTPUT32:
	case VIDIOC_ENUMOUTPUT:
	case VIDIOC_G_AUDOUT:
	case VIDIOC_S_AUDOUT:
	case VIDIOC_G_MODULATOR:
	case VIDIOC_S_MODULATOR:
	case VIDIOC_S_FREQUENCY:
	case VIDIOC_G_FREQUENCY:
	case VIDIOC_CROPCAP:
	case VIDIOC_G_CROP:
	case VIDIOC_S_CROP:
	case VIDIOC_G_JPEGCOMP:
	case VIDIOC_S_JPEGCOMP:
	case VIDIOC_QUERYSTD:
	case VIDIOC_TRY_FMT32:
	case VIDIOC_ENUMAUDIO:
	case VIDIOC_ENUMAUDOUT:
	case VIDIOC_G_PRIORITY:
	case VIDIOC_S_PRIORITY:
	case VIDIOC_G_SLICED_VBI_CAP:
	case VIDIOC_LOG_STATUS:
	case VIDIOC_G_EXT_CTRLS32:
	case VIDIOC_S_EXT_CTRLS32:
	case VIDIOC_TRY_EXT_CTRLS32:
	case VIDIOC_ENUM_FRAMESIZES:
	case VIDIOC_ENUM_FRAMEINTERVALS:
	case VIDIOC_G_ENC_INDEX:
	case VIDIOC_ENCODER_CMD:
	case VIDIOC_TRY_ENCODER_CMD:
	case VIDIOC_DBG_S_REGISTER:
	case VIDIOC_DBG_G_REGISTER:
	case VIDIOC_DBG_G_CHIP_IDENT:
	case VIDIOC_S_HW_FREQ_SEEK:
	case VIDIOC_ENUM_DV_PRESETS:
	case VIDIOC_S_DV_PRESET:
	case VIDIOC_G_DV_PRESET:
	case VIDIOC_QUERY_DV_PRESET:
	case VIDIOC_S_DV_TIMINGS:
	case VIDIOC_G_DV_TIMINGS:
	case VIDIOC_DQEVENT:
	case VIDIOC_SUBSCRIBE_EVENT:
	case VIDIOC_UNSUBSCRIBE_EVENT:
		ret = do_video_ioctl(file, cmd, arg);
		break;

	default:
		printk(KERN_WARNING "compat_ioctl32: "
			"unknown ioctl '%c', dir=%d, #%d (0x%08x)\n",
			_IOC_TYPE(cmd), _IOC_DIR(cmd), _IOC_NR(cmd), cmd);
		break;
	}
	return ret;
}
EXPORT_SYMBOL_GPL(v4l2_compat_ioctl32);
#endif

MODULE_LICENSE("GPL");
