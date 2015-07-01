#include <linux/module.h>
#if 1 /* in RHEL */
#include <linux/interrupt.h>
#endif

#ifndef __CHECKER__
#define CREATE_TRACE_POINTS
#include "trace.h"

#endif
