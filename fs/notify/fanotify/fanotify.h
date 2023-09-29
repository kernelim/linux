/* SPDX-License-Identifier: GPL-2.0 */
#include <linux/fsnotify_backend.h>
#include <linux/path.h>
#include <linux/slab.h>

extern struct kmem_cache *fanotify_mark_cache;
extern struct kmem_cache *fanotify_event_cachep;
extern struct kmem_cache *fanotify_perm_event_cachep;

/* Possible states of the permission event */
enum {
	FAN_EVENT_INIT,
	FAN_EVENT_REPORTED,
	FAN_EVENT_ANSWERED,
	FAN_EVENT_CANCELED,
};

/*
 * Structure for normal fanotify events. It gets allocated in
 * fanotify_handle_event() and freed when the information is retrieved by
 * userspace
 */
struct fanotify_event {
	struct fsnotify_event fse;
	/*
	 * We hold ref to this path so it may be dereferenced at any point
	 * during this object's lifetime
	 */
	struct path path;
	struct pid *pid;
};

/*
 * Structure for permission fanotify events. It gets allocated and freed in
 * fanotify_handle_event() since we wait there for user response. When the
 * information is retrieved by userspace the structure is moved from
 * group->notification_list to group->fanotify_data.access_list to wait for
 * user response.
 */
struct fanotify_perm_event {
	struct fanotify_event fae;
	u32 response;			/* userspace answer to the event */
	unsigned short state;		/* state of the event */
	int fd;		/* fd we passed to userspace for this event */
	union {
		struct fanotify_response_info_header hdr;
		struct fanotify_response_info_audit_rule audit_rule;
	};
};

static inline struct fanotify_perm_event *
FANOTIFY_PE(struct fsnotify_event *fse)
{
	return container_of(fse, struct fanotify_perm_event, fae.fse);
}

static inline bool fanotify_is_perm_event(u32 mask)
{
	return IS_ENABLED(CONFIG_FANOTIFY_ACCESS_PERMISSIONS) &&
		mask & FANOTIFY_PERM_EVENTS;
}

static inline struct fanotify_event *FANOTIFY_E(struct fsnotify_event *fse)
{
	return container_of(fse, struct fanotify_event, fse);
}

struct fanotify_event *fanotify_alloc_event(struct fsnotify_group *group,
						 struct inode *inode, u32 mask,
						 const struct path *path);
