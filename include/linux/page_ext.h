#ifndef __LINUX_PAGE_EXT_H
#define __LINUX_PAGE_EXT_H

#include <linux/types.h>
#include <linux/stacktrace.h>

struct page_ext_operations {
	bool (*need)(void);
	void (*init)(void);
};


/*
 * page_ext->flags bits:
 *
 * PAGE_EXT_DEBUG_POISON is set for poisoned pages. This is used to
 * implement generic debug pagealloc feature. The pages are filled with
 * poison patterns and set this flag after free_pages(). The poisoned
 * pages are verified whether the patterns are not corrupted and clear
 * the flag before alloc_pages().
 */

enum page_ext_flags {
	PAGE_EXT_DEBUG_POISON,		/* Page is poisoned */
	PAGE_EXT_DEBUG_GUARD,
	PAGE_EXT_OWNER,
#if defined(CONFIG_IDLE_PAGE_TRACKING) && !defined(CONFIG_64BIT)
	PAGE_EXT_YOUNG,
	PAGE_EXT_IDLE,
#endif
};

#ifdef CONFIG_PAGE_OWNER
struct page_owner {
	unsigned int order;
	gfp_t gfp_mask;
	unsigned int nr_entries;
	unsigned long trace_entries[8];
};
#endif
/*
 * Page Extension can be considered as an extended mem_map.
 * A page_ext page is associated with every page descriptor. The
 * page_ext helps us add more information about the page.
 * All page_ext are allocated at boot or memory hotplug event,
 * then the page_ext for pfn always exists.
 */
struct page_ext {
	unsigned long flags;
#ifdef CONFIG_PAGE_OWNER
	struct page_owner *owner;
#endif
};

#ifdef CONFIG_PAGE_EXTENSION
struct page_ext *lookup_page_ext(struct page *page);
void __init invoke_page_ext_init_callbacks(void);

#else /* !CONFIG_PAGE_EXTENSION */
static inline struct page_ext *lookup_page_ext(struct page *page)
{
	return NULL;
}

static inline void invoke_page_ext_init_callbacks(void) { }

#endif /* CONFIG_PAGE_EXTENSION */
#endif /* __LINUX_PAGE_EXT_H */
