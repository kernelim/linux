/*
 * Intel specific MCE features.
 * Copyright 2004 Zwane Mwaikambo <zwane@linuxpower.ca>
 * Copyright (C) 2008, 2009 Intel Corporation
 * Author: Andi Kleen
 */

#include <linux/gfp.h>
#include <linux/init.h>
#include <linux/interrupt.h>
#include <linux/percpu.h>
#include <linux/sched.h>
#include <linux/cpumask.h>
#include <asm/apic.h>
#include <asm/processor.h>
#include <asm/msr.h>
#include <asm/mce.h>

#include "mce-internal.h"

/*
 * Support for Intel Correct Machine Check Interrupts. This allows
 * the CPU to raise an interrupt when a corrected machine check happened.
 * Normally we pick those up using a regular polling timer.
 * Also supports reliable discovery of shared banks.
 */

static DEFINE_PER_CPU(mce_banks_t, mce_banks_owned);

/*
 * cmci_discover_lock protects against parallel discovery attempts
 * which could race against each other.
 */
static DEFINE_SPINLOCK(cmci_discover_lock);

#define CMCI_THRESHOLD		1
#define CMCI_POLL_INTERVAL	(30 * HZ)
#define CMCI_STORM_INTERVAL	(1 * HZ)
#define CMCI_STORM_THRESHOLD	15

static DEFINE_PER_CPU(unsigned long, cmci_time_stamp);
static DEFINE_PER_CPU(unsigned int, cmci_storm_cnt);
static DEFINE_PER_CPU(unsigned int, cmci_storm_state);

enum {
	CMCI_STORM_NONE,
	CMCI_STORM_ACTIVE,
	CMCI_STORM_SUBSIDED,
};

static atomic_t cmci_storm_on_cpus;

static int cmci_supported(int *banks)
{
	u64 cap;

	if (mce_cmci_disabled || mce_ignore_ce)
		return 0;

	/*
	 * Vendor check is not strictly needed, but the initial
	 * initialization is vendor keyed and this
	 * makes sure none of the backdoors are entered otherwise.
	 */
	if (boot_cpu_data.x86_vendor != X86_VENDOR_INTEL)
		return 0;
	if (!cpu_has_apic || lapic_get_maxlvt() < 6)
		return 0;
	rdmsrl(MSR_IA32_MCG_CAP, cap);
	*banks = min_t(unsigned, MAX_NR_BANKS, cap & 0xff);
	return !!(cap & MCG_CMCI_P);
}

void mce_intel_cmci_poll(void)
{
	if (__get_cpu_var(cmci_storm_state) == CMCI_STORM_NONE)
		return;
	machine_check_poll(MCP_TIMESTAMP, &__get_cpu_var(mce_banks_owned));
}

void mce_intel_hcpu_update(unsigned long cpu)
{
	if (per_cpu(cmci_storm_state, cpu) == CMCI_STORM_ACTIVE)
		atomic_dec(&cmci_storm_on_cpus);

	per_cpu(cmci_storm_state, cpu) = CMCI_STORM_NONE;
}

unsigned long mce_intel_adjust_timer(unsigned long interval)
{
	int r;
	unsigned int *state = &__get_cpu_var(cmci_storm_state);

	if (interval < CMCI_POLL_INTERVAL)
		return interval;

	switch (*state) {
	case CMCI_STORM_ACTIVE:
		/*
		 * We switch back to interrupt mode once the poll timer has
		 * silenced itself. That means no events recorded and the
		 * timer interval is back to our poll interval.
		 */
		*state = CMCI_STORM_SUBSIDED;
		r = atomic_sub_return(1, &cmci_storm_on_cpus);
		if (r == 0)
			pr_notice("CMCI storm subsided: switching to interrupt mode\n");
		/* FALLTHROUGH */

	case CMCI_STORM_SUBSIDED:
		/*
		 * We wait for all cpus to go back to SUBSIDED
		 * state. When that happens we switch back to
		 * interrupt mode.
		 */
		if (!atomic_read(&cmci_storm_on_cpus)) {
			*state = CMCI_STORM_NONE;
			cmci_reenable();
			cmci_recheck();
		}
		return CMCI_POLL_INTERVAL;
	default:
		/*
		 * We have shiny weather. Let the poll do whatever it
		 * thinks.
		 */
		return interval;
	}
}

static void cmci_storm_disable_banks(void)
{
	unsigned long flags, *owned;
	int bank;
	u64 val;

	spin_lock_irqsave(&cmci_discover_lock, flags);
	owned = __get_cpu_var(mce_banks_owned);
	for_each_set_bit(bank, owned, MAX_NR_BANKS) {
		rdmsrl(MSR_IA32_MCx_CTL2(bank), val);
		val &= ~MCI_CTL2_CMCI_EN;
		wrmsrl(MSR_IA32_MCx_CTL2(bank), val);
	}
	spin_unlock_irqrestore(&cmci_discover_lock, flags);
}

static bool cmci_storm_detect(void)
{
	unsigned int *state = &__get_cpu_var(cmci_storm_state);
	unsigned int *cnt = &__get_cpu_var(cmci_storm_cnt);
	unsigned long *ts = &__get_cpu_var(cmci_time_stamp);
	unsigned long now = jiffies;
	int r;

	if (*state != CMCI_STORM_NONE)
		return true;

	if (time_before_eq(now, *ts + CMCI_STORM_INTERVAL)) {
		(*cnt)++;
	} else {
		*cnt = 1;
		*ts = now;
	}

	if (*cnt <= CMCI_STORM_THRESHOLD)
		return false;

	cmci_storm_disable_banks();
	*state = CMCI_STORM_ACTIVE;
	r = atomic_add_return(1, &cmci_storm_on_cpus);
	mce_timer_kick(CMCI_POLL_INTERVAL);

	if (r == 1)
		pr_notice("CMCI storm detected: switching to poll mode\n");
	return true;
}

/*
 * The interrupt handler. This is called on every event.
 * Just call the poller directly to log any events.
 * This could in theory increase the threshold under high load,
 * but doesn't for now.
 */
static void intel_threshold_interrupt(void)
{
	if (cmci_storm_detect())
		return;
	machine_check_poll(MCP_TIMESTAMP, &__get_cpu_var(mce_banks_owned));
	mce_notify_irq();
}

/*
 * Enable CMCI (Corrected Machine Check Interrupt) for available MCE banks
 * on this CPU. Use the algorithm recommended in the SDM to discover shared
 * banks.
 */
static void cmci_discover(int banks)
{
	unsigned long *owned = (void *)&__get_cpu_var(mce_banks_owned);
	unsigned long flags;
	int i;
	int bios_wrong_thresh = 0;

	spin_lock_irqsave(&cmci_discover_lock, flags);
	for (i = 0; i < banks; i++) {
		u64 val;
		int bios_zero_thresh = 0;

		if (test_bit(i, owned))
			continue;

		/* Skip banks in firmware first mode */
		if (test_bit(i, mce_banks_ce_disabled))
			continue;

		rdmsrl(MSR_IA32_MCx_CTL2(i), val);

		/* Already owned by someone else? */
		if (val & MCI_CTL2_CMCI_EN) {
			clear_bit(i, owned);
			__clear_bit(i, __get_cpu_var(mce_poll_banks));
			continue;
		}

		if (!mce_bios_cmci_threshold) {
			val &= ~MCI_CTL2_CMCI_THRESHOLD_MASK;
			val |= CMCI_THRESHOLD;
		} else if (!(val & MCI_CTL2_CMCI_THRESHOLD_MASK)) {
			/*
			 * If bios_cmci_threshold boot option was specified
			 * but the threshold is zero, we'll try to initialize
			 * it to 1.
			 */
			bios_zero_thresh = 1;
			val |= CMCI_THRESHOLD;
		}

		val |= MCI_CTL2_CMCI_EN;
		wrmsrl(MSR_IA32_MCx_CTL2(i), val);
		rdmsrl(MSR_IA32_MCx_CTL2(i), val);

		/* Did the enable bit stick? -- the bank supports CMCI */
		if (val & MCI_CTL2_CMCI_EN) {
			set_bit(i, owned);
			__clear_bit(i, __get_cpu_var(mce_poll_banks));
			/*
			 * We are able to set thresholds for some banks that
			 * had a threshold of 0. This means the BIOS has not
			 * set the thresholds properly or does not work with
			 * this boot option. Note down now and report later.
			 */
			if (mce_bios_cmci_threshold && bios_zero_thresh &&
					(val & MCI_CTL2_CMCI_THRESHOLD_MASK))
				bios_wrong_thresh = 1;
		} else {
			WARN_ON(!test_bit(i, __get_cpu_var(mce_poll_banks)));
		}
	}
	spin_unlock_irqrestore(&cmci_discover_lock, flags);
	if (mce_bios_cmci_threshold && bios_wrong_thresh) {
		pr_info_once(
			"bios_cmci_threshold: Some banks do not have valid thresholds set\n");
		pr_info_once(
			"bios_cmci_threshold: Make sure your BIOS supports this boot option\n");
	}
}

/*
 * Just in case we missed an event during initialization check
 * all the CMCI owned banks.
 */
void cmci_recheck(void)
{
	unsigned long flags;
	int banks;

	if (!mce_available(&current_cpu_data) || !cmci_supported(&banks))
		return;
	local_irq_save(flags);
	machine_check_poll(MCP_TIMESTAMP, &__get_cpu_var(mce_banks_owned));
	local_irq_restore(flags);
}

/* Caller must hold the lock on cmci_discover_lock */
static void __cmci_disable_bank(int bank)
{
	u64 val;

	if (!test_bit(bank, __get_cpu_var(mce_banks_owned)))
		return;
	rdmsrl(MSR_IA32_MCx_CTL2(bank), val);
	val &= ~MCI_CTL2_CMCI_EN;
	wrmsrl(MSR_IA32_MCx_CTL2(bank), val);
	__clear_bit(bank, __get_cpu_var(mce_banks_owned));
}

/*
 * Disable CMCI on this CPU for all banks it owns when it goes down.
 * This allows other CPUs to claim the banks on rediscovery.
 */
void cmci_clear(void)
{
	unsigned long flags;
	int i;
	int banks;

	if (!cmci_supported(&banks))
		return;
	spin_lock_irqsave(&cmci_discover_lock, flags);
	for (i = 0; i < banks; i++)
		__cmci_disable_bank(i);
	spin_unlock_irqrestore(&cmci_discover_lock, flags);
}

/*
 * After a CPU went down cycle through all the others and rediscover
 * Must run in process context.
 */
void cmci_rediscover(int dying)
{
	int banks;
	int cpu;
	cpumask_var_t old;

	if (!cmci_supported(&banks))
		return;
	if (!alloc_cpumask_var(&old, GFP_KERNEL))
		return;
	cpumask_copy(old, &current->cpus_allowed);

	for_each_online_cpu(cpu) {
		if (cpu == dying)
			continue;
		if (set_cpus_allowed_ptr(current, cpumask_of(cpu)))
			continue;
		/* Recheck banks in case CPUs don't all have the same */
		if (cmci_supported(&banks))
			cmci_discover(banks);
	}

	set_cpus_allowed_ptr(current, old);
	free_cpumask_var(old);
}

/*
 * Reenable CMCI on this CPU in case a CPU down failed.
 */
void cmci_reenable(void)
{
	int banks;
	if (cmci_supported(&banks))
		cmci_discover(banks);
}

void cmci_disable_bank(int bank)
{
	int banks;
	unsigned long flags;

	if (!cmci_supported(&banks))
		return;

	spin_lock_irqsave(&cmci_discover_lock, flags);
	__cmci_disable_bank(bank);
	spin_unlock_irqrestore(&cmci_discover_lock, flags);
}

static void intel_init_cmci(void)
{
	int banks;

	if (!cmci_supported(&banks))
		return;

	mce_threshold_vector = intel_threshold_interrupt;
	cmci_discover(banks);
	/*
	 * For CPU #0 this runs with still disabled APIC, but that's
	 * ok because only the vector is set up. We still do another
	 * check for the banks later for CPU #0 just to make sure
	 * to not miss any events.
	 */
	apic_write(APIC_LVTCMCI, THRESHOLD_APIC_VECTOR|APIC_DM_FIXED);
	cmci_recheck();
}

void mce_intel_feature_init(struct cpuinfo_x86 *c)
{
	intel_init_thermal(c);
	intel_init_cmci();
}
