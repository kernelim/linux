/*
 * Detect hard and soft lockups on a system
 *
 * started by Don Zickus, Copyright (C) 2010 Red Hat, Inc.
 *
 * this code detects hard lockups: incidents in where on a CPU
 * the kernel does not respond to anything except NMI.
 *
 * Note: Most of this code is borrowed heavily from softlockup.c,
 * so thanks to Ingo for the initial implementation.
 * Some chunks also taken from arch/x86/kernel/apic/nmi.c, thanks
 * to those contributors as well.
 */

#include <linux/mm.h>
#include <linux/cpu.h>
#include <linux/nmi.h>
#include <linux/init.h>
#include <linux/delay.h>
#include <linux/freezer.h>
#include <linux/kthread.h>
#include <linux/lockdep.h>
#include <linux/notifier.h>
#include <linux/module.h>
#include <linux/sysctl.h>

#include <asm/irq_regs.h>
#include <linux/kvm_para.h>
#include <linux/perf_event.h>

int watchdog_enabled = 1;
int __read_mostly softlockup_thresh = 60;
#ifdef CONFIG_SMP
int __read_mostly sysctl_softlockup_all_cpu_backtrace;
int __read_mostly sysctl_hardlockup_all_cpu_backtrace;
#else
#define sysctl_softlockup_all_cpu_backtrace 0
#define sysctl_hardlockup_all_cpu_backtrace 0
#endif


static DEFINE_PER_CPU(unsigned long, watchdog_touch_ts);
static DEFINE_PER_CPU(struct task_struct *, softlockup_watchdog);
static DEFINE_PER_CPU(struct hrtimer, watchdog_hrtimer);
static DEFINE_PER_CPU(bool, softlockup_touch_sync);
static DEFINE_PER_CPU(bool, soft_watchdog_warn);
#ifdef CONFIG_HARDLOCKUP_DETECTOR
static DEFINE_PER_CPU(bool, hard_watchdog_warn);
static DEFINE_PER_CPU(bool, watchdog_nmi_touch);
static DEFINE_PER_CPU(unsigned long, hrtimer_interrupts);
static DEFINE_PER_CPU(unsigned long, hrtimer_interrupts_saved);
static DEFINE_PER_CPU(struct perf_event *, watchdog_ev);
#endif
static unsigned long soft_lockup_nmi_warn;

/* boot commands */
/*
 * Should we panic when a soft-lockup or hard-lockup occurs:
 */
#ifdef CONFIG_HARDLOCKUP_DETECTOR
unsigned int __read_mostly hardlockup_panic =
			CONFIG_BOOTPARAM_HARDLOCKUP_PANIC_VALUE;
static int hardlockup_enable = 
			CONFIG_BOOTPARAM_HARDLOCKUP_ENABLED_VALUE;

static bool hardlockup_detector_enabled = true;
static unsigned long hardlockup_allcpu_dumped;
/*
 * We may not want to enable hard lockup detection by default in all cases,
 * for example when running the kernel as a guest on a hypervisor. In these
 * cases this function can be called to disable hard lockup detection. This
 * function should only be executed once by the boot processor before the
 * kernel command line parameters are parsed, because otherwise it is not
 * possible to override this in hardlockup_panic_setup().
 */
void watchdog_enable_hardlockup_detector(bool val)
{
	hardlockup_detector_enabled = val;
}

bool watchdog_hardlockup_detector_is_enabled(void)
{
	return hardlockup_detector_enabled;
}

static int __init hardlockup_panic_setup(char *str)
{
	if (!strncmp(str, "panic", 5))
		hardlockup_panic = 1;
	else if (!strncmp(str, "nopanic", 7))
		hardlockup_panic = 0;
	else if (!strncmp(str, "0", 1))
		watchdog_enabled = 0;
	else if (!strncmp(str, "1", 1) ||
		 !strncmp(str, "2", 1))
	{
		hardlockup_enable = 1;
		watchdog_enable_hardlockup_detector(true);
	}
	else if (!strncmp(str, "lapic", 5) ||
		 !strncmp(str, "ioapic", 6))
	{
		hardlockup_enable = 1;
		watchdog_enable_hardlockup_detector(true);
	}
	return 1;
}
__setup("nmi_watchdog=", hardlockup_panic_setup);
#endif

unsigned int __read_mostly softlockup_panic =
			CONFIG_BOOTPARAM_SOFTLOCKUP_PANIC_VALUE;

static int __init softlockup_panic_setup(char *str)
{
	softlockup_panic = simple_strtoul(str, NULL, 0);

	return 1;
}
__setup("softlockup_panic=", softlockup_panic_setup);

static int __init nowatchdog_setup(char *str)
{
	watchdog_enabled = 0;
	return 1;
}
__setup("nowatchdog", nowatchdog_setup);

/* deprecated */
static int __init nosoftlockup_setup(char *str)
{
	watchdog_enabled = 0;
	return 1;
}
__setup("nosoftlockup", nosoftlockup_setup);
/*  */
#ifdef CONFIG_SMP
static int __init softlockup_all_cpu_backtrace_setup(char *str)
{
	sysctl_softlockup_all_cpu_backtrace =
		!!simple_strtol(str, NULL, 0);
	return 1;
}
__setup("softlockup_all_cpu_backtrace=", softlockup_all_cpu_backtrace_setup);
static int __init hardlockup_all_cpu_backtrace_setup(char *str)
{
	sysctl_hardlockup_all_cpu_backtrace =
		!!simple_strtol(str, NULL, 0);
	return 1;
}
__setup("hardlockup_all_cpu_backtrace=", hardlockup_all_cpu_backtrace_setup);
#endif


/*
 * Returns seconds, approximately.  We don't need nanosecond
 * resolution, and we don't need to waste time with a big divide when
 * 2^30ns == 1.074s.
 */
static unsigned long get_timestamp(int this_cpu)
{
	return cpu_clock(this_cpu) >> 30LL;  /* 2^30 ~= 10^9 */
}

static unsigned long get_sample_period(void)
{
	/*
	 * convert softlockup_thresh from seconds to ns
	 * the divide by 5 is to give hrtimer 5 chances to
	 * increment before the hardlockup detector generates
	 * a warning
	 */
	return softlockup_thresh / 5 * NSEC_PER_SEC;
}

/* Commands for resetting the watchdog */
static void __touch_watchdog(void)
{
	int this_cpu = smp_processor_id();

	__get_cpu_var(watchdog_touch_ts) = get_timestamp(this_cpu);
}

void touch_softlockup_watchdog(void)
{
	__raw_get_cpu_var(watchdog_touch_ts) = 0;
}
EXPORT_SYMBOL(touch_softlockup_watchdog);

void touch_all_softlockup_watchdogs(void)
{
	int cpu;

	/*
	 * this is done lockless
	 * do we care if a 0 races with a timestamp?
	 * all it means is the softlock check starts one cycle later
	 */
	for_each_online_cpu(cpu)
		per_cpu(watchdog_touch_ts, cpu) = 0;
}

#ifdef CONFIG_HARDLOCKUP_DETECTOR
void touch_nmi_watchdog(void)
{
	/*
	 * Using __raw here because some code paths have
	 * preemption enabled.  If preemption is enabled
	 * then interrupts should be enabled too, in which
	 * case we shouldn't have to worry about the watchdog
	 * going off.
	 */
	__raw_get_cpu_var(watchdog_nmi_touch) = true;
	touch_softlockup_watchdog();
}
EXPORT_SYMBOL(touch_nmi_watchdog);

#endif

void touch_softlockup_watchdog_sync(void)
{
	__raw_get_cpu_var(softlockup_touch_sync) = true;
	__raw_get_cpu_var(watchdog_touch_ts) = 0;
}

#ifdef CONFIG_HARDLOCKUP_DETECTOR
/* watchdog detector functions */
static int is_hardlockup(void)
{
	unsigned long hrint = __get_cpu_var(hrtimer_interrupts);

	if (__get_cpu_var(hrtimer_interrupts_saved) == hrint)
		return 1;

	__get_cpu_var(hrtimer_interrupts_saved) = hrint;
	return 0;
}
#endif

static int is_softlockup(unsigned long touch_ts)
{
	unsigned long now = get_timestamp(smp_processor_id());

	/* Warn about unreasonable delays: */
	if (time_after(now, touch_ts + softlockup_thresh))
		return now - touch_ts;

	return 0;
}

#ifdef CONFIG_HARDLOCKUP_DETECTOR

static struct perf_event_attr wd_hw_attr = {
	.type		= PERF_TYPE_HARDWARE,
	.config		= PERF_COUNT_HW_CPU_CYCLES,
	.size		= sizeof(struct perf_event_attr),
	.pinned		= 1,
	.disabled	= 1,
};

/* Callback function for perf event subsystem */
static void watchdog_overflow_callback(struct perf_event *event,
		 struct perf_sample_data *data,
		 struct pt_regs *regs)
{
	/* Ensure the watchdog never gets throttled */
	event->hw.interrupts = 0;

	if (__get_cpu_var(watchdog_nmi_touch) == true) {
		__get_cpu_var(watchdog_nmi_touch) = false;
		return;
	}

	/* check for a hardlockup
	 * This is done by making sure our timer interrupt
	 * is incrementing.  The timer interrupt should have
	 * fired multiple times before we overflow'd.  If it hasn't
	 * then this is a good indication the cpu is stuck
	 */
	if (is_hardlockup()) {
		int this_cpu = smp_processor_id();
		struct pt_regs *regs = get_irq_regs();

		/* only print hardlockups once */
		if (__get_cpu_var(hard_watchdog_warn) == true)
			return;

		pr_emerg("Watchdog detected hard LOCKUP on cpu %d", this_cpu);
		print_modules();
		print_irqtrace_events(current);
		if (regs)
			show_regs(regs);
		else
			dump_stack();

		/*
		 * Perform all-CPU dump only once to avoid multiple hardlockups
		 * generating interleaving traces
		 */
		if (sysctl_hardlockup_all_cpu_backtrace &&
				!test_and_set_bit(0, &hardlockup_allcpu_dumped))
			trigger_allbutself_cpu_backtrace();

		if (hardlockup_panic)
			panic("Hard LOCKUP");

		__get_cpu_var(hard_watchdog_warn) = true;
		return;
	}

	__get_cpu_var(hard_watchdog_warn) = false;
	return;
}
static void watchdog_interrupt_count(void)
{
	__get_cpu_var(hrtimer_interrupts)++;
}
#else
static inline void watchdog_interrupt_count(void) { return; }
#endif /* CONFIG_HARDLOCKUP_DETECTOR */

/* watchdog kicker functions */
static enum hrtimer_restart watchdog_timer_fn(struct hrtimer *hrtimer)
{
	unsigned long touch_ts = __get_cpu_var(watchdog_touch_ts);
	struct pt_regs *regs = get_irq_regs();
	int duration;
	int softlockup_all_cpu_backtrace = sysctl_softlockup_all_cpu_backtrace;

	/* kick the hardlockup detector */
	watchdog_interrupt_count();

	/* kick the softlockup detector */
	wake_up_process(__get_cpu_var(softlockup_watchdog));

	/* .. and repeat */
	hrtimer_forward_now(hrtimer, ns_to_ktime(get_sample_period()));

	if (touch_ts == 0) {
		if (unlikely(__get_cpu_var(softlockup_touch_sync))) {
			/*
			 * If the time stamp was touched atomically
			 * make sure the scheduler tick is up to date.
			 */
			__get_cpu_var(softlockup_touch_sync) = false;
			sched_clock_tick();
		}

		/* Clear the guest paused flag on watchdog reset */
		kvm_check_and_clear_guest_paused();
		__touch_watchdog();
		return HRTIMER_RESTART;
	}

	/* check for a softlockup
	 * This is done by making sure a high priority task is
	 * being scheduled.  The task touches the watchdog to
	 * indicate it is getting cpu time.  If it hasn't then
	 * this is a good indication some task is hogging the cpu
	 */
	duration = is_softlockup(touch_ts);
	if (unlikely(duration)) {
		/*
		 * If a virtual machine is stopped by the host it can look to
		 * the watchdog like a soft lockup, check to see if the host
		 * stopped the vm before we issue the warning
		 */
		if (kvm_check_and_clear_guest_paused())
			return HRTIMER_RESTART;

		/* only warn once */
		if (__get_cpu_var(soft_watchdog_warn) == true)
			return HRTIMER_RESTART;

		if (softlockup_all_cpu_backtrace) {
			/* Prevent multiple soft-lockup reports if one cpu is already
			 * engaged in dumping cpu back traces
			 */
			if (test_and_set_bit(0, &soft_lockup_nmi_warn)) {
				/* Someone else will report us. Let's give up */
				__get_cpu_var(soft_watchdog_warn) = true;
				return HRTIMER_RESTART;
			}
		}

		printk(KERN_EMERG "BUG: soft lockup - CPU#%d stuck for %us! [%s:%d]\n",
			smp_processor_id(), duration,
			current->comm, task_pid_nr(current));
		print_modules();
		print_irqtrace_events(current);
		if (regs)
			show_regs(regs);
		else
			dump_stack();

		if (softlockup_all_cpu_backtrace) {
			/* Avoid generating two back traces for current
			 * given that one is already made above
			 */
			trigger_allbutself_cpu_backtrace();

			clear_bit(0, &soft_lockup_nmi_warn);
			/* Barrier to sync with other cpus */
			smp_mb__after_clear_bit();
		}

		add_taint(TAINT_SOFTLOCKUP);
		if (softlockup_panic)
			panic("softlockup: hung tasks");
		__get_cpu_var(soft_watchdog_warn) = true;
	} else
		__get_cpu_var(soft_watchdog_warn) = false;

	return HRTIMER_RESTART;
}


/*
 * The watchdog thread - touches the timestamp.
 */
static int watchdog(void *unused)
{
	struct sched_param param = { .sched_priority = 0 };
	struct hrtimer *hrtimer = &__raw_get_cpu_var(watchdog_hrtimer);

	/* initialize timestamp */
	__touch_watchdog();

	/* kick off the timer for the hardlockup detector */
	/* done here because hrtimer_start can only pin to smp_processor_id() */
	hrtimer_start(hrtimer, ns_to_ktime(get_sample_period()),
		      HRTIMER_MODE_REL_PINNED);

	set_current_state(TASK_INTERRUPTIBLE);
	/*
	 * Run briefly once per second to reset the softlockup timestamp.
	 * If this gets delayed for more than 60 seconds then the
	 * debug-printout triggers in watchdog_timer_fn().
	 */
	while (!kthread_should_stop()) {
		__touch_watchdog();
		schedule();

		if (kthread_should_stop())
			break;

		set_current_state(TASK_INTERRUPTIBLE);
	}
	__set_current_state(TASK_RUNNING);
	sched_setscheduler(current, SCHED_NORMAL, &param);
	return 0;
}


#ifdef CONFIG_HARDLOCKUP_DETECTOR
/*
 * People like the simple clean cpu node info on boot.
 * Reduce the watchdog noise by only printing messages
 * that are different from what cpu0 displayed.
 */
static unsigned long cpu0_err;

static int watchdog_nmi_enable(unsigned int cpu)
{
	struct perf_event_attr *wd_attr;
	struct perf_event *event = per_cpu(watchdog_ev, cpu);

	if (!hardlockup_enable)
		return 0;

	/*
	 * Some kernels need to default hard lockup detection to
	 * 'disabled', for example a guest on a hypervisor.
	 */
	if (!watchdog_hardlockup_detector_is_enabled()) {
		event = ERR_PTR(-ENOENT);
		goto handle_err;
	}

	/* is it already setup and enabled? */
	if (event && event->state > PERF_EVENT_STATE_OFF)
		goto out;

	/* it is setup but not enabled */
	if (event != NULL)
		goto out_enable;

	wd_attr = &wd_hw_attr;
	wd_attr->sample_period = hw_nmi_get_sample_period();

	/* Try to register using hardware perf events */
	event = perf_event_create_kernel_counter(wd_attr, cpu, NULL, watchdog_overflow_callback, NULL);

handle_err:
	/* save cpu0 error for future comparision */
	if (cpu == 0 && IS_ERR(event))
		cpu0_err = PTR_ERR(event);

	if (!IS_ERR(event)) {
		/* only print for cpu0 or different than cpu0 */
		if (cpu == 0 || cpu0_err)
			printk(KERN_INFO "NMI watchdog enabled, takes one hw-pmu counter.\n");
		goto out_save;
	}

	/* skip displaying the same error again */
	if (cpu > 0 && (PTR_ERR(event) == cpu0_err))
		return PTR_ERR(event);

	/* vary the KERN level based on the returned errno */
	if (PTR_ERR(event) == -EOPNOTSUPP)
		printk(KERN_INFO "NMI watchdog disabled (cpu%i): not supported (no LAPIC?)\n", cpu);
	else if (PTR_ERR(event) == -ENOENT)
		printk(KERN_WARNING "NMI watchdog disabled (cpu%i): hardware events not enabled\n", cpu);
	else
		printk(KERN_ERR "NMI watchdog disabled (cpu%i): unable to create perf event: %ld\n", cpu, PTR_ERR(event));
	return PTR_ERR(event);

	/* success path */
out_save:
	per_cpu(watchdog_ev, cpu) = event;
out_enable:
	perf_event_enable(per_cpu(watchdog_ev, cpu));
out:
	return 0;
}

static void watchdog_nmi_disable(unsigned int cpu)
{
	struct perf_event *event = per_cpu(watchdog_ev, cpu);

	if (event) {
		perf_event_disable(event);
		per_cpu(watchdog_ev, cpu) = NULL;

		/* should be in cleanup, but blocks oprofile */
		perf_event_release_kernel(event);
	}
	if (cpu == 0) {
		/* watchdog_nmi_enable() expects this to be zero initially. */
		cpu0_err = 0;
	}
}

void watchdog_nmi_enable_all(void)
{
	int cpu;

	if (!watchdog_enabled)
		return;

	get_online_cpus();
	for_each_online_cpu(cpu)
		watchdog_nmi_enable(cpu);
	put_online_cpus();
}

void watchdog_nmi_disable_all(void)
{
	int cpu;

	if (!watchdog_enabled)
		return;

	get_online_cpus();
	for_each_online_cpu(cpu)
		watchdog_nmi_disable(cpu);
	put_online_cpus();
}
#else
static int watchdog_nmi_enable(unsigned int cpu) { return 0; }
static void watchdog_nmi_disable(unsigned int cpu) { return; }
void watchdog_nmi_enable_all(void) {}
void watchdog_nmi_disable_all(void) {}
#endif /* CONFIG_HARDLOCKUP_DETECTOR */

/* prepare/enable/disable routines */
static int watchdog_prepare_cpu(int cpu)
{
	struct hrtimer *hrtimer = &per_cpu(watchdog_hrtimer, cpu);

	WARN_ON(per_cpu(softlockup_watchdog, cpu));
	hrtimer_init(hrtimer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
	hrtimer->function = watchdog_timer_fn;

	return 0;
}

static int watchdog_enable(int cpu)
{
	struct task_struct *p = per_cpu(softlockup_watchdog, cpu);
	int err = 0;

	/* enable the perf event */
	err = watchdog_nmi_enable(cpu);

	/* Regardless of err above, fall through and start softlockup */

	/* create the watchdog thread */
	if (!p) {
		struct sched_param param = { .sched_priority = MAX_RT_PRIO-1 };
		p = kthread_create(watchdog, (void *)(unsigned long)cpu, "watchdog/%d", cpu);
		if (IS_ERR(p)) {
			printk(KERN_ERR "softlockup watchdog for %i failed\n", cpu);
			if (!err)
				/* if hardlockup hasn't already set this */
				err = PTR_ERR(p);
			goto out;
		}
		sched_setscheduler(p, SCHED_FIFO, &param);
		kthread_bind(p, cpu);
		per_cpu(watchdog_touch_ts, cpu) = 0;
		per_cpu(softlockup_watchdog, cpu) = p;
		wake_up_process(p);
	}

out:
	return err;
}

static void watchdog_disable(int cpu)
{
	struct task_struct *p = per_cpu(softlockup_watchdog, cpu);
	struct hrtimer *hrtimer = &per_cpu(watchdog_hrtimer, cpu);

	/*
	 * cancel the timer first to stop incrementing the stats
	 * and waking up the kthread
	 */
	hrtimer_cancel(hrtimer);

	/* disable the perf event */
	watchdog_nmi_disable(cpu);

	/* stop the watchdog thread */
	if (p) {
		per_cpu(softlockup_watchdog, cpu) = NULL;
		kthread_stop(p);
	}
}

static void restart_watchdog_hrtimer(void *info)
{
	struct hrtimer *hrtimer = &__raw_get_cpu_var(watchdog_hrtimer);
	int ret;

	/*
	 * No need to cancel and restart hrtimer if it is currently executing
	 * because it will reprogram itself with the new period now.
	 * We should never see it unqueued here because we are running per-cpu
	 * with interrupts disabled.
	 */
	ret = hrtimer_try_to_cancel(hrtimer);
	if (ret == 1)
		hrtimer_start(hrtimer, ns_to_ktime(get_sample_period()),
				HRTIMER_MODE_REL_PINNED);
}

static void update_timers(int cpu)
{
	struct call_single_data data = {.func = restart_watchdog_hrtimer};
	/*
	 * Make sure that perf event counter will adopt to a new
	 * sampling period. Updating the sampling period directly would
	 * be much nicer but we do not have an API for that now so
	 * let's use a big hammer.
	 * Hrtimer will adopt the new period on the next tick but this
	 * might be late already so we have to restart the timer as well.
	 */
	watchdog_nmi_disable(cpu);
	__smp_call_function_single(cpu, &data, 1);
	watchdog_nmi_enable(cpu);
}

static void update_timers_all_cpus(void)
{
	int cpu;

	preempt_disable();
	for_each_online_cpu(cpu)
		update_timers(cpu);
	preempt_enable();
}

static void watchdog_enable_all_cpus(void)
{
	int cpu;

	watchdog_enabled = 0;

#ifdef CONFIG_HARDLOCKUP_DETECTOR
	/* user is explicitly enabling this */
	hardlockup_enable = 1;
	watchdog_enable_hardlockup_detector(true);
#endif
	for_each_online_cpu(cpu)
		if (!watchdog_enable(cpu))
			/* if any cpu succeeds, watchdog is considered
			   enabled for the system */
			watchdog_enabled = 1;

	if (!watchdog_enabled)
		printk(KERN_ERR "watchdog: failed to be enabled on some cpus\n");

}

static void watchdog_disable_all_cpus(void)
{
	int cpu;

	for_each_online_cpu(cpu)
		watchdog_disable(cpu);

	/* if all watchdogs are disabled, then they are disabled for the system */
	watchdog_enabled = 0;
}


/* sysctl functions */
#ifdef CONFIG_SYSCTL
static DEFINE_MUTEX(watchdog_proc_mutex);
/*
 * proc handler for /proc/sys/kernel/nmi_watchdog
 */

int proc_dowatchdog_enabled(struct ctl_table *table, int write,
		     void __user *buffer, size_t *length, loff_t *ppos)
{
	get_online_cpus();
	mutex_lock(&watchdog_proc_mutex);
	proc_dointvec(table, write, buffer, length, ppos);

	if (write) {
		if (watchdog_enabled)
			watchdog_enable_all_cpus();
		else
			watchdog_disable_all_cpus();
	}
	mutex_unlock(&watchdog_proc_mutex);
	put_online_cpus();
	return 0;
}

int proc_dowatchdog_thresh(struct ctl_table *table, int write,
			     void __user *buffer,
			     size_t *lenp, loff_t *ppos)
{
	int err;

	get_online_cpus();
	mutex_lock(&watchdog_proc_mutex);
	err = proc_dointvec_minmax(table, write, buffer, lenp, ppos);
	if (err || !write)
		goto out;

	if (watchdog_enabled)
		update_timers_all_cpus();
out:
	mutex_unlock(&watchdog_proc_mutex);
	put_online_cpus();
	return err;
}
#endif /* CONFIG_SYSCTL */


/*
 * Create/destroy watchdog threads as CPUs come and go:
 */
static int __cpuinit
cpu_callback(struct notifier_block *nfb, unsigned long action, void *hcpu)
{
	int hotcpu = (unsigned long)hcpu;
	int err = 0;

	switch (action) {
	case CPU_UP_PREPARE:
	case CPU_UP_PREPARE_FROZEN:
		err = watchdog_prepare_cpu(hotcpu);
		break;
	case CPU_ONLINE:
	case CPU_ONLINE_FROZEN:
		if (watchdog_enabled)
			err = watchdog_enable(hotcpu);
		break;
#ifdef CONFIG_HOTPLUG_CPU
	case CPU_UP_CANCELED:
	case CPU_UP_CANCELED_FROZEN:
		watchdog_disable(hotcpu);
		break;
	case CPU_DEAD:
	case CPU_DEAD_FROZEN:
		watchdog_disable(hotcpu);
		break;
#endif /* CONFIG_HOTPLUG_CPU */
	}

	/*
	 * hardlockup and softlockup are not important enough
	 * to block cpu bring up.  Just always succeed and
	 * rely on printk output to flag problems.
	 */
	return NOTIFY_OK;
}

static struct notifier_block __cpuinitdata cpu_nfb = {
	.notifier_call = cpu_callback
};

void __init lockup_detector_init(void)
{
	void *cpu = (void *)(long)smp_processor_id();
	int err;

	err = cpu_callback(&cpu_nfb, CPU_UP_PREPARE, cpu);
	WARN_ON(notifier_to_errno(err));

	cpu_callback(&cpu_nfb, CPU_ONLINE, cpu);
	register_cpu_notifier(&cpu_nfb);

	return;
}
