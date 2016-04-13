#ifndef __KERNEL_PRINTK__
#define __KERNEL_PRINTK__

#include <linux/kernel.h>

typedef int(*printk_func_t)(const char *fmt, va_list args);

#endif
