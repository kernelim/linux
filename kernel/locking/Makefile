# SPDX-License-Identifier: GPL-2.0
# Any varying coverage in these files is non-deterministic
# and is generally not a function of system call inputs.
KCOV_INSTRUMENT		:= n

obj-y += mutex.o semaphore.o rwsem.o percpu-rwsem.o rwsem_init.o

# Avoid recursion lockdep -> KCSAN -> ... -> lockdep.
KCSAN_SANITIZE_lockdep.o := n

ifdef CONFIG_FUNCTION_TRACER
CFLAGS_REMOVE_lockdep.o = $(CC_FLAGS_FTRACE)
CFLAGS_REMOVE_lockdep_proc.o = $(CC_FLAGS_FTRACE)
CFLAGS_REMOVE_mutex-debug.o = $(CC_FLAGS_FTRACE)
endif

obj-$(CONFIG_DEBUG_IRQFLAGS) += irqflag-debug.o
obj-$(CONFIG_DEBUG_MUTEXES) += mutex-debug.o
obj-$(CONFIG_LOCKDEP) += lockdep.o
ifeq ($(CONFIG_PROC_FS),y)
obj-$(CONFIG_LOCKDEP) += lockdep_proc.o
endif
obj-$(CONFIG_SMP) += spinlock.o
obj-$(CONFIG_LOCK_SPIN_ON_OWNER) += osq_lock.o
obj-$(CONFIG_PROVE_LOCKING) += spinlock.o
obj-$(CONFIG_QUEUED_SPINLOCKS) += qspinlock.o
obj-$(CONFIG_RT_MUTEXES) += rtmutex_api.o
obj-$(CONFIG_PREEMPT_RT) += spinlock_rt.o ww_rt_mutex.o
obj-$(CONFIG_DEBUG_SPINLOCK) += spinlock.o
obj-$(CONFIG_DEBUG_SPINLOCK) += spinlock_debug.o
obj-$(CONFIG_QUEUED_RWLOCKS) += qrwlock.o
obj-$(CONFIG_LOCK_TORTURE_TEST) += locktorture.o
obj-$(CONFIG_WW_MUTEX_SELFTEST) += test-ww_mutex.o
obj-$(CONFIG_LOCK_EVENT_COUNTS) += lock_events.o

#
# Generate RHEL8 specific file for __init_rwsem() function to perserve kABI.
#
$(obj)/rwsem_init.c: $(src)/rwsem.c
	@(echo "#include <linux/sched/signal.h>";	\
	  echo "#include <linux/rwsem.h>";		\
	  echo "#ifndef CONFIG_PREEMPT_RT") > $(obj)/rwsem_init.c
	@sed -n -e "/^void __init_rwsem(/,/^EXPORT_SYMBOL(__init_rwsem)/p" \
		-e "/^EXPORT_SYMBOL(__init_rwsem)/q" $(srctree)/$(src)/rwsem.c \
		>> $(obj)/rwsem_init.c
	@echo "#endif" >> $(obj)/rwsem_init.c
