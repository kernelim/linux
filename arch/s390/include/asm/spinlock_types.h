#ifndef __ASM_SPINLOCK_TYPES_H
#define __ASM_SPINLOCK_TYPES_H

#ifndef __LINUX_SPINLOCK_TYPES_H
# error "please don't include this file directly"
#endif

typedef struct {
#ifndef __GENKSYMS__
	unsigned int lock;
#else
	volatile unsigned int owner_cpu;
#endif
} __attribute__ ((aligned (4))) raw_spinlock_t;

#define __RAW_SPIN_LOCK_UNLOCKED { .lock = 0, }

typedef struct {
#ifndef __GENKSYMS__
	unsigned int lock;
#else
	volatile unsigned int lock;
#endif
} raw_rwlock_t;

#define __RAW_RW_LOCK_UNLOCKED		{ 0 }

#endif
