#ifndef _INCLUDE_KAISER_H
#define _INCLUDE_KAISER_H

#ifdef CONFIG_PAGE_TABLE_ISOLATION
#include <asm/kaiser.h>
#else
#ifndef __ASSEMBLY__
/*
 * These stubs are used whenever CONFIG_PAGE_TABLE_ISOLATION is off, which
 * includes architectures that support KAISER, but have it
 * disabled.
 */

static inline void kaiser_early_init(bool preset)
{
}

static inline void kaiser_init(void)
{
}

static inline void kaiser_remove_mapping(unsigned long start, unsigned long size)
{
}

static inline int kaiser_add_mapping(unsigned long addr, unsigned long size,
				     u64 flags)
{
	return 0;
}

static inline bool kaiser_active(void)
{
	return 0;
}
#endif /* __ASSEMBLY__ */
#endif /* !CONFIG_PAGE_TABLE_ISOLATION */
#endif /* _INCLUDE_KAISER_H */
