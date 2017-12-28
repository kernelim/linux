#ifndef LINUX_MM_DEBUG_H
#define LINUX_MM_DEBUG_H 1

#include <linux/autoconf.h>

#ifdef CONFIG_DEBUG_VM
#define VM_BUG_ON(cond) BUG_ON(cond)
#define VM_WARN_ON(cond) WARN_ON(cond)
#define VM_WARN_ON_ONCE(cond) WARN_ON_ONCE(cond)
#else
#define VM_BUG_ON(cond) do { } while (0)
#define VM_WARN_ON(cond) ((void)(sizeof((__force long)(cond))))
#define VM_WARN_ON_ONCE(cond) ((void)(sizeof((__force long)(cond))))
#endif

#ifdef CONFIG_DEBUG_VIRTUAL
#define VIRTUAL_BUG_ON(cond) BUG_ON(cond)
#else
#define VIRTUAL_BUG_ON(cond) do { } while (0)
#endif

#endif
