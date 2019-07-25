/*
 *  Copyright (C) 2017  Red Hat, Inc.
 *
 *  This work is licensed under the terms of the GNU GPL, version 2. See
 *  the COPYING file in the top-level directory.
 */

#include <linux/cpu.h>
#include <linux/percpu.h>
#include <linux/debugfs.h>
#include <linux/uaccess.h>
#include <linux/sched.h>
#include <asm/spec_ctrl.h>
#include <asm/cpufeature.h>
#include <asm/nospec-branch.h>
#include <asm/cpu.h>
#include "cpu/cpu.h"

static DEFINE_MUTEX(spec_ctrl_mutex);

static bool noibrs_cmdline __read_mostly;
static bool ibp_disabled __read_mostly;
unsigned int ibrs_mode __read_mostly;
EXPORT_SYMBOL(ibrs_mode);

/*
 * The vendor and possibly platform specific bits which can be modified in
 * x86_spec_ctrl_base.
 *
 */
u64 __read_mostly x86_spec_ctrl_mask = SPEC_CTRL_IBRS|SPEC_CTRL_SSBD;
EXPORT_SYMBOL_GPL(x86_spec_ctrl_mask);

/*
 * The Intel specification for the SPEC_CTRL MSR requires that we
 * preserve any already set reserved bits at boot time (e.g. for
 * future additions that this kernel is not currently aware of).
 * We then set any additional mitigation bits that we want
 * ourselves and always use this as the base for SPEC_CTRL.
 * We also use this when handling guest entry/exit as below.
 *
 * RHEL note: We do the above to be in sync with upstream,
 * but in the RHEL case, we have both x86_spec_ctrl_base,
 * and a PER_CPU spec_ctrl_pcp to track and manage.
 *
 * RHEL note: It's actually cleaner to directly export this
 * and allow all of our assorted IBRS management code to touch
 * this directly, rather than use the upstream accessors. We
 * implement them, but we don't use those in the RHEL code.
 */

/*
 * Our boot-time value of the SPEC_CTRL MSR. We read it once so that any
 * writes to SPEC_CTRL contain whatever reserved bits have been set.
 */
u64 __read_mostly x86_spec_ctrl_base;
EXPORT_SYMBOL_GPL(x86_spec_ctrl_base);
static bool spec_ctrl_msr_write;

/*
 * AMD specific MSR info for Store Bypass control.
 * x86_amd_ls_cfg_ssbd_mask is initialized in identify_boot_cpu().
 */
u64 __read_mostly x86_amd_ls_cfg_base;
u64 __read_mostly x86_amd_ls_cfg_ssbd_mask;

void spec_ctrl_save_msr(void)
{
	int cpu;
	unsigned int hival, loval;
	static int savecnt;

	spec_ctrl_msr_write = false;

	/* Allow STIBP in MSR_SPEC_CTRL if supported */
	if (boot_cpu_has(X86_FEATURE_STIBP))
		x86_spec_ctrl_mask |= SPEC_CTRL_STIBP;

	/*
	 * Read the SPEC_CTRL MSR to account for reserved bits which may have
	 * unknown values. AMD64_LS_CFG MSR is cached in the early AMD
	 * init code as it is not enumerated and depends on the family.
	 */
	if (boot_cpu_has(X86_FEATURE_MSR_SPEC_CTRL) && !savecnt) {
		/*
		 * This part is run only the first time it is called.
		 */
		rdmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
		if (x86_spec_ctrl_base & x86_spec_ctrl_mask) {
			x86_spec_ctrl_base &= ~x86_spec_ctrl_mask;
			spec_ctrl_msr_write = true;
			native_wrmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
		}
	}

	/*
	 * RHEL only: update the PER_CPU spec_ctrl_pcp cached values
	 */

	loval = x86_spec_ctrl_base & 0xffffffff;
	hival = (x86_spec_ctrl_base >> 32) & 0xffffffff;

	for_each_possible_cpu(cpu) {
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.hi32, cpu), hival);
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.entry, cpu), loval);
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.exit, cpu), loval);
	}
	savecnt++;
}

/*
 * This is called for setting the entry or exit values in the spec_ctrl_pcp
 * structure when the SSDB is user settable. The state of the SSBD bit
 * is maintained.
 */
static void set_spec_ctrl_value(unsigned int *ptr, unsigned int value)
{
	unsigned int old, new, val;

	old = READ_ONCE(*ptr);
	for (;;) {
		new = value | (old & SPEC_CTRL_SSBD);
		val = cmpxchg(ptr, old, new);
		if (val == old)
			break;
		old = val;
	}
}

static void set_spec_ctrl_pcp(bool entry, bool exit)
{
	unsigned int enabled   = percpu_read(spec_ctrl_pcp.enabled);
	unsigned int entry_val = percpu_read(spec_ctrl_pcp.entry);
	unsigned int exit_val  = percpu_read(spec_ctrl_pcp.exit);
	int cpu, redo_cnt;
	/*
	 * Set if the SSBD bit of the SPEC_CTRL MSR is user settable.
	 */
	bool ssb_user_settable = boot_cpu_has(X86_FEATURE_SPEC_CTRL_SSBD) &&
				 ssb_is_user_settable(READ_ONCE(ssb_mode));

	/*
	 * Mask off the SSBD bit first if it is user settable.
	 * Otherwise, make sure that the SSBD bit of the entry and exit
	 * values match that of the x86_spec_ctrl_base.
	 */
	if (ssb_user_settable) {
		entry_val &= ~SPEC_CTRL_SSBD;
		exit_val  &= ~SPEC_CTRL_SSBD;
	} else {
		entry_val = (entry_val & ~SPEC_CTRL_SSBD) |
			    (x86_spec_ctrl_base & SPEC_CTRL_SSBD);
		exit_val  = (exit_val & ~SPEC_CTRL_SSBD) |
			    (x86_spec_ctrl_base & SPEC_CTRL_SSBD);
	}

	/*
	 * For ibrs_always, we only need to write the MSR at kernel entry
	 * to fulfill the barrier semantics for some CPUs.
	 */
	if (entry && exit)
		enabled = SPEC_CTRL_PCP_IBRS_ENTRY;
	else if (entry != exit)
		enabled = SPEC_CTRL_PCP_IBRS_ENTRY|SPEC_CTRL_PCP_IBRS_EXIT;
	else
		enabled = 0;

	if (entry)
		entry_val |= SPEC_CTRL_IBRS;
	else
		entry_val &= ~SPEC_CTRL_IBRS;

	if (exit)
		exit_val |= SPEC_CTRL_IBRS;
	else
		exit_val &= ~SPEC_CTRL_IBRS;

	for_each_possible_cpu(cpu) {
		unsigned int *pentry = &per_cpu(spec_ctrl_pcp.entry, cpu);
		unsigned int *pexit  = &per_cpu(spec_ctrl_pcp.exit, cpu);

		WRITE_ONCE(per_cpu(spec_ctrl_pcp.enabled, cpu), enabled);
		if (!ssb_user_settable) {
			WRITE_ONCE(*pentry, entry_val);
			WRITE_ONCE(*pexit, exit_val);
		} else {
			/*
			 * Since the entry and exit fields can be modified
			 * concurrently by spec_ctrl_set_ssbd() to set or
			 * clear the SSBD bit, We need to maintain the
			 * SSBD bit and use atomic instruction to do the
			 * modification here.
			 */
			set_spec_ctrl_value(pentry, entry_val);
			set_spec_ctrl_value(pexit, exit_val);
		}
	}

	if (!ssb_user_settable)
		return;

	/*
	 * Because of the non-atomic read-modify-write nature of
	 * spec_ctrl_set_ssbd() function, the atomic entry/exit value changes
	 * above may be lost. So we need to recheck it again and reapply the
	 * change, if necessary.
	 */
recheck:
	redo_cnt = 0;
	smp_mb();
	for_each_possible_cpu(cpu) {
		unsigned int *pentry = &per_cpu(spec_ctrl_pcp.entry, cpu);
		unsigned int *pexit  = &per_cpu(spec_ctrl_pcp.exit, cpu);

		if ((READ_ONCE(*pentry) & ~SPEC_CTRL_SSBD) != entry_val) {
			set_spec_ctrl_value(pentry, entry_val);
			redo_cnt++;
		}
		if ((READ_ONCE(*pexit) & ~SPEC_CTRL_SSBD) != exit_val) {
			set_spec_ctrl_value(pexit, exit_val);
			redo_cnt++;
		}
	}
	if (redo_cnt)
		goto recheck;
}

/*
 * The following values are written to IBRS on kernel entry/exit:
 *
 *		entry	exit
 * ibrs		  1	 0
 * ibrs_always	  1	 1
 * ibrs_user	  0	 1
 */

static void set_spec_ctrl_pcp_ibrs(void)
{
	set_spec_ctrl_pcp(true, false);
	ibrs_mode = IBRS_ENABLED;
}

static void set_spec_ctrl_pcp_ibrs_always(void)
{
	set_spec_ctrl_pcp(true, true);
	ibrs_mode = IBRS_ENABLED_ALWAYS;
}

static void set_spec_ctrl_pcp_ibrs_user(void)
{
	set_spec_ctrl_pcp(false, true);
	ibrs_mode = IBRS_ENABLED_USER;
}

void clear_spec_ctrl_pcp(void)
{
	set_spec_ctrl_pcp(false, false);
	ibrs_mode = IBRS_DISABLED;
}

static void sync_all_cpus_spec_ctrl(void)
{
	int cpu;
	get_online_cpus();
	for_each_online_cpu(cpu)
		wrmsrl_on_cpu(cpu, MSR_IA32_SPEC_CTRL, SPEC_CTRL_MSR_REFRESH);
	put_online_cpus();
}

static void __sync_this_cpu_ibp(void *data)
{
	bool enable = *(bool *)data;
	u64 val;

	/* disable IBP on old CPU families */
	rdmsrl(MSR_F15H_IC_CFG, val);
	if (!enable)
		val |= MSR_F15H_IC_CFG_DIS_IND;
	else
		val &= ~MSR_F15H_IC_CFG_DIS_IND;
	wrmsrl(MSR_F15H_IC_CFG, val);
}

/* enable means IBP should be enabled in the CPU (i.e. fast) */
static void sync_all_cpus_ibp(bool enable)
{
	get_online_cpus();

	__sync_this_cpu_ibp(&enable);

	smp_call_function_many(cpu_online_mask, __sync_this_cpu_ibp,
			       &enable, 1);

	put_online_cpus();
}

static void spec_ctrl_disable_all(void)
{
	int cpu;

	for_each_possible_cpu(cpu)
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.enabled, cpu), 0);
	spectre_v2_retpoline_reset();
}

static int __init noibrs(char *str)
{
	noibrs_cmdline = true;

	return 0;
}
early_param("noibrs", noibrs);

static int __init noibpb(char *str)
{
	/* deprecated */
	return 0;
}
early_param("noibpb", noibpb);

bool spec_ctrl_force_enable_ibrs(void)
{
	if (cpu_has_spec_ctrl()) {
		set_spec_ctrl_pcp_ibrs();
		spectre_v2_set_mitigation(SPECTRE_V2_IBRS);
		return true;
	}

	return false;
}

bool spec_ctrl_cond_enable_ibrs(bool full_retp)
{
	if (cpu_has_spec_ctrl() && (is_skylake_era() || !full_retp) &&
	    !noibrs_cmdline) {
		set_spec_ctrl_pcp_ibrs();
		spectre_v2_set_mitigation(SPECTRE_V2_IBRS);
		/*
		 * Print a warning message about performance
		 * impact of enabling IBRS vs. retpoline.
		 */
		pr_warn_once("Using IBRS as the default Spectre v2 mitigation for a Skylake-\n");
		pr_warn_once("generation CPU.  This may have a negative performance impact.\n");
		return true;
	}

	return false;
}

bool spec_ctrl_enable_ibrs_always(void)
{
	if (cpu_has_spec_ctrl()) {
		set_spec_ctrl_pcp_ibrs_always();
		spectre_v2_set_mitigation(SPECTRE_V2_IBRS_ALWAYS);
		return true;
	}

	return false;
}

bool spec_ctrl_force_enable_ibp_disabled(void)
{
	/*
	 * Some AMD CPUs don't need IBPB or IBRS CPUID bits, because
	 * they can just disable indirect branch predictor
	 * support (MSR 0xc0011021[14]).
	 */
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		ibp_disabled = true;
		spectre_v2_set_mitigation(SPECTRE_V2_IBP_DISABLED);
		return true;
	}

	ibp_disabled = false;
	return false;
}

bool spec_ctrl_cond_enable_ibp_disabled(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE) && !noibrs_cmdline) {
		ibp_disabled = true;
		spectre_v2_set_mitigation(SPECTRE_V2_IBP_DISABLED);
		return true;
	}

	ibp_disabled = false;
	return false;
}

void spec_ctrl_enable_retpoline_ibrs_user(void)
{
	if (!cpu_has_spec_ctrl() || !spectre_v2_has_full_retpoline())
		return;

	set_spec_ctrl_pcp_ibrs_user();
	spectre_v2_set_mitigation(SPECTRE_V2_RETPOLINE_IBRS_USER);
	return;
}

static void spec_ctrl_print_features(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		printk_once(KERN_INFO "FEATURE SPEC_CTRL Present (Implicit)\n");
		printk_once(KERN_INFO "FEATURE IBPB_SUPPORT Present (Implicit)\n");
		return;
	}

	if (cpu_has_spec_ctrl())
		printk_once(KERN_INFO "FEATURE SPEC_CTRL Present\n");
	else
		printk_once(KERN_INFO "FEATURE SPEC_CTRL Not Present\n");

	if (boot_cpu_has(X86_FEATURE_IBPB))
		printk_once(KERN_INFO "FEATURE IBPB_SUPPORT Present\n");
	else
		printk_once(KERN_INFO "FEATURE IBPB_SUPPORT Not Present\n");
}

void spec_ctrl_cpu_init(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		bool enabled = !ibp_disabled;
		__sync_this_cpu_ibp(&enabled);
		return;
	}

	if ((ibrs_mode == IBRS_ENABLED_ALWAYS) ||
	    (spec_ctrl_msr_write && (system_state == SYSTEM_BOOTING)))
		native_wrmsr(MSR_IA32_SPEC_CTRL,
			     percpu_read(spec_ctrl_pcp.entry),
			     percpu_read(spec_ctrl_pcp.hi32));
}

static void spec_ctrl_reinit_all_cpus(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		sync_all_cpus_ibp(!ibrs_mode);
		return;
	}

	if ((ibrs_mode == IBRS_ENABLED_ALWAYS) ||
	    (ibrs_mode == IBRS_DISABLED) || spec_ctrl_msr_write) {
		sync_all_cpus_spec_ctrl();
		spec_ctrl_msr_write = false;
	}
}

void spec_ctrl_init(void)
{
	spec_ctrl_print_features();
}

void spec_ctrl_rescan_cpuid(void)
{
	enum spectre_v2_mitigation old_mode;
	bool old_ibrs, old_ibpb, old_ssbd, old_l1df, old_mds;
	bool ssbd_changed;
	int cpu;

	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE))
		return;

	mutex_lock(&spec_ctrl_mutex);
	if (boot_cpu_data.x86_vendor == X86_VENDOR_INTEL ||
	    boot_cpu_data.x86_vendor == X86_VENDOR_AMD) {
		old_ibrs = boot_cpu_has(X86_FEATURE_IBRS);
		old_ibpb = boot_cpu_has(X86_FEATURE_IBPB);
		old_ssbd = boot_cpu_has(X86_FEATURE_SSBD);
		old_l1df = boot_cpu_has(X86_FEATURE_FLUSH_L1D);
		old_mds  = boot_cpu_has(X86_FEATURE_MD_CLEAR);
		old_mode = spectre_v2_get_mitigation();

		/* detect spec ctrl related cpuid additions */
		get_cpu_cap(&boot_cpu_data);

		/*
		 * Populate the FLUSH_L1D cap bit to each CPU if it changes.
		 */
		if (!old_l1df && boot_cpu_has(X86_FEATURE_FLUSH_L1D))
			for_each_online_cpu(cpu)
				set_cpu_cap(&cpu_data(cpu), X86_FEATURE_FLUSH_L1D);

		/*
		 * If there were no spec ctrl or mds related changes,
		 * we're done.
		 */
		ssbd_changed = (old_ssbd != boot_cpu_has(X86_FEATURE_SSBD));
		if (old_ibrs == boot_cpu_has(X86_FEATURE_IBRS) &&
		    old_ibpb == boot_cpu_has(X86_FEATURE_IBPB) &&
		    old_mds  == boot_cpu_has(X86_FEATURE_MD_CLEAR) &&
		    !ssbd_changed)
			goto done;

		/* Update the boot CPU microcode version */
		boot_cpu_data.microcode = cpu_data(0).microcode;
		check_bad_spectre_microcode(&boot_cpu_data);

		/*
		 * The IBRS, IBPB & SSBD cpuid bits may have
		 * just been set in the boot_cpu_data, transfer them
		 * to the per-cpu data too.
		 */
		if (cpu_has_spec_ctrl())
			for_each_online_cpu(cpu)
				set_cpu_cap(&cpu_data(cpu), X86_FEATURE_IBRS);
		if (boot_cpu_has(X86_FEATURE_IBPB))
			for_each_online_cpu(cpu)
				set_cpu_cap(&cpu_data(cpu), X86_FEATURE_IBPB);
		if (boot_cpu_has(X86_FEATURE_SSBD))
			for_each_online_cpu(cpu)
				set_cpu_cap(&cpu_data(cpu), X86_FEATURE_SSBD);
		if (boot_cpu_has(X86_FEATURE_MD_CLEAR))
			for_each_online_cpu(cpu)
				set_cpu_cap(&cpu_data(cpu),
					    X86_FEATURE_MD_CLEAR);

		/* print the changed IBRS/IBPB features */
		spec_ctrl_print_features();

		if (ssbd_changed) {
			u64 old_spec_ctrl = x86_spec_ctrl_base;

			/*
			 * Redo speculation store bypass setup.
			 */
			ssb_select_mitigation();
			if (x86_spec_ctrl_base != old_spec_ctrl) {
				/*
				 * Need to propagate the new baseline to all
				 * the percpu spec_ctrl structures. The
				 * spectre v2 re-initialization below will
				 * reset the right percpu values.
				 */
				spec_ctrl_save_msr();
				spec_ctrl_msr_write = true;

			}
		}

		/*
		 * Re-execute the v2 mitigation logic based on any new CPU
		 * features.  Note that any debugfs-based changes the user may
		 * have made will be overwritten, because new features are now
		 * available, so any previous changes may no longer be
		 * relevant.  Go back to the defaults unless they're overridden
		 * by the cmdline.
		 */
		spec_ctrl_disable_all();
		__spectre_v2_select_mitigation();
		spec_ctrl_reinit_all_cpus();

		/* print any mitigation changes */
		if (old_mode != spectre_v2_get_mitigation())
			spectre_v2_print_mitigation();

		/*
		 * Look for X86_FEATURE_MD_CLEAR change for CPUs that are
		 * vulnerable to MDS & reflect that in the mds vulnerabilities
		 * file.
		 */
		if (boot_cpu_has_bug(X86_BUG_MDS) &&
		   (mds_mitigation != MDS_MITIGATION_OFF)) {
			enum mds_mitigations new;

			new = boot_cpu_has(X86_FEATURE_MD_CLEAR)
			    ? MDS_MITIGATION_FULL : MDS_MITIGATION_VMWERV;
			if (new != mds_mitigation) {
				mds_mitigation = new;
				mds_print_mitigation();
			}
		}
	}
done:
	mutex_unlock(&spec_ctrl_mutex);
}
EXPORT_SYMBOL_GPL(spec_ctrl_rescan_cpuid);

/*
 * Change the SSBD bit of the spec_ctrl structure of the current CPU.
 * The caller has to make sure that preemption is disabled so that
 * no CPU change is possible during the call.
 *
 * Since spec_ctrl_set_ssbd() is in the fast path, we are not doing
 * any atomic update to the entry and exit values. The percpu logical
 * operation used here is a single non-atomic read-modify-write instruction.
 * As a result, we need to do more checking at the slowpath set_spec_ctrl_pcp()
 * function to make sure that any changes in the ibrs_enabled value get
 * reflected correctly in all the spec_ctrl_pcp structures.
 */
void spec_ctrl_set_ssbd(bool ssbd_on)
{
	if (ssbd_on) {
		percpu_or(spec_ctrl_pcp.entry, SPEC_CTRL_SSBD);
		percpu_or(spec_ctrl_pcp.exit,  SPEC_CTRL_SSBD);
	} else {
		percpu_and(spec_ctrl_pcp.entry, ~SPEC_CTRL_SSBD);
		percpu_and(spec_ctrl_pcp.exit,  ~SPEC_CTRL_SSBD);
	}
}

static ssize_t __enabled_read(struct file *file, char __user *user_buf,
			      size_t count, loff_t *ppos, unsigned int *field)
{
	char buf[32];
	unsigned int len;

	len = sprintf(buf, "%d\n", READ_ONCE(*field));
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t ibrs_enabled_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	unsigned int enabled = ibrs_mode;

	if (ibp_disabled)
		enabled = IBRS_ENABLED_ALWAYS;

	return __enabled_read(file, user_buf, count, ppos, &enabled);
}

static ssize_t ibrs_enabled_write(struct file *file,
				  const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	char buf[32];
	ssize_t len;
	unsigned int enable;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;

	buf[len] = '\0';
	if (kstrtouint(buf, 0, &enable))
		return -EINVAL;

	if (enable > IBRS_MAX)
		return -EINVAL;

	mutex_lock(&spec_ctrl_mutex);
	if ((!ibp_disabled && enable == ibrs_mode) ||
	    (ibp_disabled && enable == IBRS_ENABLED_ALWAYS))
		goto out_unlock;

	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		if (enable == IBRS_ENABLED || enable == IBRS_ENABLED_USER) {
			count = -EINVAL;
			goto out_unlock;
		}

		if (enable == IBRS_DISABLED) {
			sync_all_cpus_ibp(true);
			ibp_disabled = false;
			spectre_v2_retpoline_reset();
		} else {
			WARN_ON(enable != IBRS_ENABLED_ALWAYS);
			sync_all_cpus_ibp(false);
			ibp_disabled = true;
			spectre_v2_set_mitigation(SPECTRE_V2_IBP_DISABLED);
		}
		goto out_unlock;
	}

	if (!cpu_has_spec_ctrl()) {
		count = -ENODEV;
		goto out_unlock;
	}

	if (enable == IBRS_DISABLED) {
		clear_spec_ctrl_pcp();
		sync_all_cpus_spec_ctrl();
		spectre_v2_retpoline_reset();
	} else if (enable == IBRS_ENABLED) {
		set_spec_ctrl_pcp_ibrs();
		spectre_v2_set_mitigation(SPECTRE_V2_IBRS);
	} else if (enable == IBRS_ENABLED_ALWAYS) {
		set_spec_ctrl_pcp_ibrs_always();
		sync_all_cpus_spec_ctrl();
		spectre_v2_set_mitigation(SPECTRE_V2_IBRS_ALWAYS);
	} else {
		WARN_ON(enable != IBRS_ENABLED_USER);
		if (!spectre_v2_has_full_retpoline()) {
			count = -ENODEV;
			goto out_unlock;
		}
		set_spec_ctrl_pcp_ibrs_user();
		spectre_v2_set_mitigation(SPECTRE_V2_RETPOLINE_IBRS_USER);
	}

out_unlock:
	mutex_unlock(&spec_ctrl_mutex);
	return count;
}

static const struct file_operations fops_ibrs_enabled = {
	.read = ibrs_enabled_read,
	.write = ibrs_enabled_write,
	.llseek = default_llseek,
};

static ssize_t ibpb_enabled_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	unsigned int enabled = ibpb_enabled();

	if (ibp_disabled)
		enabled = 1;

	return __enabled_read(file, user_buf, count, ppos, &enabled);
}

static const struct file_operations fops_ibpb_enabled = {
	.read = ibpb_enabled_read,
	.llseek = default_llseek,
};

static ssize_t retp_enabled_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	unsigned int enabled = !!boot_cpu_has(X86_FEATURE_RETPOLINE);

	return __enabled_read(file, user_buf, count, ppos, &enabled);
}

static const struct file_operations fops_retp_enabled = {
	.read = retp_enabled_read,
	.llseek = default_llseek,
};

/*
 * The ssb_mode variable controls the state of the Speculative Store Bypass
 * Disable (SSBD) mitigation.
 *  0 - SSBD is disabled (speculative store bypass is enabled).
 *  1 - SSBD is enabled  (speculative store bypass is disabled).
 *  2 - SSBD is controlled by prctl only.
 *  3 - SSBD is controlled by both prctl and seccomp.
 */
static ssize_t ssbd_enabled_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	unsigned int enabled = ssb_mode;
	return __enabled_read(file, user_buf, count, ppos, &enabled);
}

static void ssbd_spec_ctrl_write(unsigned int mode)
{
	/*
	 * We have to update the x86_spec_ctrl_base first and then all the
	 * SPEC_CTRL MSRs. We also need to update the ssb_mode prior to
	 * that if the new mode isn't user settable to make sure that
	 * the existing SSBD bit in the spec_ctrl_pcp won't carry over.
	 */
	if (!ssb_is_user_settable(mode))
		set_mb(ssb_mode, mode);

	switch (ibrs_mode) {
		case IBRS_DISABLED:
			clear_spec_ctrl_pcp();
			break;
		case IBRS_ENABLED:
			set_spec_ctrl_pcp_ibrs();
			break;
		case IBRS_ENABLED_ALWAYS:
			set_spec_ctrl_pcp_ibrs_always();
			break;
		case IBRS_ENABLED_USER:
			set_spec_ctrl_pcp_ibrs_user();
			break;
	}
	sync_all_cpus_spec_ctrl();
}

static void ssbd_amd_write(unsigned int mode)
{
	u64 msrval;
	int msr, cpu;

	if (boot_cpu_has(X86_FEATURE_VIRT_SSBD)) {
		msr    = MSR_AMD64_VIRT_SPEC_CTRL;
		msrval = (mode == SPEC_STORE_BYPASS_DISABLE)
		       ? SPEC_CTRL_SSBD : 0;
	} else {
		msr    = MSR_AMD64_LS_CFG;
		msrval = x86_amd_ls_cfg_base;
		if (mode == SPEC_STORE_BYPASS_DISABLE)
			msrval |= x86_amd_ls_cfg_ssbd_mask;
	}

	/*
	 * If the new mode isn't settable, we have to update the
	 * ssb_mode first.
	 */
	if (!ssb_is_user_settable(mode))
		set_mb(ssb_mode, mode);

	/*
	 * If the old mode isn't user settable, it is assumed that no
	 * existing task will have the TIF_SSBD bit set. So we can safely
	 * overwrite the MSRs.
	 */
	get_online_cpus();
	for_each_online_cpu(cpu)
		wrmsrl_on_cpu(cpu, msr, msrval);
	put_online_cpus();
}

static ssize_t ssbd_enabled_write(struct file *file,
				  const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	char buf[32];
	ssize_t len;
	unsigned int mode;
	const unsigned int mode_max = IS_ENABLED(CONFIG_SECCOMP)
				    ? SPEC_STORE_BYPASS_SECCOMP
				    : SPEC_STORE_BYPASS_PRCTL;

	if (!boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS) ||
	    !boot_cpu_has(X86_FEATURE_SSBD))
		return -ENODEV;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;

	buf[len] = '\0';
	if (kstrtouint(buf, 0, &mode))
		return -EINVAL;

	if (mode > mode_max)
		return -EINVAL;

	mutex_lock(&spec_ctrl_mutex);

	if (mode == ssb_mode)
		goto out_unlock;

	/* Set/clear the SSBD bit in x86_spec_ctrl_base accordingly */
	if (mode == SPEC_STORE_BYPASS_DISABLE)
		x86_spec_ctrl_base |= SPEC_CTRL_SSBD;
	else
		x86_spec_ctrl_base &= ~SPEC_CTRL_SSBD;

	/*
	 * If both the old and new SSB modes are user settable or it is
	 * transitioning from SPEC_STORE_BYPASS_NONE to a user settable
	 * mode, we don't need to touch the spec_ctrl_pcp structure or the
	 * AMD LS_CFG MSRs at all and so the change can be made directly.
	 */
	if (ssb_is_user_settable(mode) &&
	   (ssb_is_user_settable(ssb_mode) ||
	   (ssb_mode == SPEC_STORE_BYPASS_NONE)))
		goto out;

	if (boot_cpu_has(X86_FEATURE_SPEC_CTRL_SSBD))
		ssbd_spec_ctrl_write(mode);
	else if (boot_cpu_has(X86_FEATURE_LS_CFG_SSBD) ||
		 boot_cpu_has(X86_FEATURE_VIRT_SSBD))
		ssbd_amd_write(mode);

out:
	WRITE_ONCE(ssb_mode, mode);
	ssb_print_mitigation();
out_unlock:
	mutex_unlock(&spec_ctrl_mutex);
	return count;
}

static const struct file_operations fops_ssbd_enabled = {
	.read = ssbd_enabled_read,
	.write = ssbd_enabled_write,
	.llseek = default_llseek,
};

static ssize_t smt_present_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	unsigned int present = atomic_read(&sched_smt_present);

	return __enabled_read(file, user_buf, count, ppos, &present);
}

static const struct file_operations fops_smt_present = {
	.read = smt_present_read,
	.llseek = default_llseek,
};

static int __init debugfs_spec_ctrl(void)
{
	debugfs_create_file("ibrs_enabled", S_IRUSR | S_IWUSR,
			    arch_debugfs_dir, NULL, &fops_ibrs_enabled);
	debugfs_create_file("ibpb_enabled", S_IRUSR,
			    arch_debugfs_dir, NULL, &fops_ibpb_enabled);
	debugfs_create_file("retp_enabled", S_IRUSR,
			    arch_debugfs_dir, NULL, &fops_retp_enabled);
	debugfs_create_file("ssbd_enabled", S_IRUSR,
			    arch_debugfs_dir, NULL, &fops_ssbd_enabled);
	debugfs_create_file("smt_present", S_IRUSR,
			    arch_debugfs_dir, NULL, &fops_smt_present);
	return 0;
}
late_initcall(debugfs_spec_ctrl);

#if defined(RETPOLINE)
/*
 * RETPOLINE does not protect against indirect speculation
 * in firmware code.  Enable IBRS to protect firmware execution.
 */
bool unprotected_firmware_begin(void)
{
	return spec_ctrl_ibrs_on_firmware();
}
EXPORT_SYMBOL_GPL(unprotected_firmware_begin);

void unprotected_firmware_end(bool ibrs_on)
{
	spec_ctrl_ibrs_off_firmware(ibrs_on);
}
EXPORT_SYMBOL_GPL(unprotected_firmware_end);

#else
bool unprotected_firmware_begin(void)
{
	return false;
}
EXPORT_SYMBOL_GPL(unprotected_firmware_begin);

void unprotected_firmware_end(bool ibrs_on)
{
}
EXPORT_SYMBOL_GPL(unprotected_firmware_end);
#endif
