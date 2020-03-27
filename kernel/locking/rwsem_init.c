// SPDX-License-Identifier: GPL-2.0
/*
 * RHEL8 specific file for __init_rwsem() function to perserve kABI.
 */
#define RWSEM_INIT_ONLY
#include <linux/sched/signal.h>
#include "rwsem.c"
