#include <linux/module.h>
#if 1 /* in RHEL6 */
#include <linux/interrupt.h>
#endif

#ifndef __CHECKER__
#define CREATE_TRACE_POINTS
#include "trace.h"

#endif
