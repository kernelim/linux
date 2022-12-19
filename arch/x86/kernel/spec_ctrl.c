/*
 *  Copyright (C) 2017  Red Hat, Inc.
 *
 *  This work is licensed under the terms of the GNU GPL, version 2. See
 *  the COPYING file in the top-level directory.
 */

#include <linux/percpu.h>
#include <linux/debugfs.h>
#include <linux/uaccess.h>
#include <linux/module.h>
#include <linux/sched/smt.h>
#include <asm/spec_ctrl.h>
#include <asm/cpufeature.h>
#include <asm/nospec-branch.h>
#include <asm/intel-family.h>
#include "cpu/cpu.h"

static DEFINE_MUTEX(spec_ctrl_mutex);

static bool noibrs_cmdline __read_mostly;
static bool ibp_disabled __read_mostly;
static bool unsafe_module __read_mostly;
static bool retpoline_amd_mode __read_mostly;
static unsigned int ibrs_mode __read_mostly;

/*
 * The ssbd_userset_key is set to true if the SSDB mode is user settable.
 */
struct static_key ssbd_userset_key = STATIC_KEY_INIT_FALSE;
struct static_key retp_enabled_key = STATIC_KEY_INIT_FALSE;
struct static_key ibrs_present_key = STATIC_KEY_INIT_FALSE;
struct static_key ibrs_entry_key   = STATIC_KEY_INIT_FALSE;
struct static_key ibrs_exit_key    = STATIC_KEY_INIT_FALSE;
struct static_key ibpb_enabled_key = STATIC_KEY_INIT_FALSE;
EXPORT_SYMBOL(ssbd_userset_key);
EXPORT_SYMBOL(retp_enabled_key);
EXPORT_SYMBOL(ibrs_present_key);
EXPORT_SYMBOL(ibpb_enabled_key);

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
 * AMD specific MSR info for Store Bypass control.  x86_amd_ls_cfg_ssbd_mask
 * is initialized in identify_boot_cpu().
 */
u64 __read_mostly x86_amd_ls_cfg_base;
u64 __read_mostly x86_amd_ls_cfg_ssbd_mask;

static inline bool ssb_is_user_settable(unsigned int mode)
{
	return mode >= SPEC_STORE_BYPASS_PRCTL;
}

/*
 * Set the static key to match the given boolean flag
 */
static inline void set_static_key(struct static_key *key, bool enable)
{
	if (enable && !static_key_enabled(key))
		static_key_slow_inc(key);
	else if (!enable && static_key_enabled(key))
		static_key_slow_dec(key);
}

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
	unsigned int enabled   = this_cpu_read(spec_ctrl_pcp.enabled);
	unsigned int entry_val = this_cpu_read(spec_ctrl_pcp.entry);
	unsigned int exit_val  = this_cpu_read(spec_ctrl_pcp.exit);
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
	 * to fulfill the barrier semantics for some CPUs. For enhanced
	 * IBRS, we don't need to write the MSR at kernel entry/exit anymore.
	 */
	if (entry && exit)
		enabled = (ibrs_mode == IBRS_ENHANCED)
			? 0 : SPEC_CTRL_PCP_IBRS_ENTRY;
	else if (entry != exit)
		enabled = SPEC_CTRL_PCP_IBRS_ENTRY|SPEC_CTRL_PCP_IBRS_EXIT;
	else
		enabled = 0;

	/*
	 * Set ibrs_entry_key and ibrs_exit_key to match the enabled flag.
	 */
	set_static_key(&ibrs_entry_key, enabled & SPEC_CTRL_PCP_IBRS_ENTRY);
	set_static_key(&ibrs_exit_key , enabled & SPEC_CTRL_PCP_IBRS_EXIT);

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

static void set_spec_ctrl_ibpb(bool enable)
{
	if (boot_cpu_has(X86_FEATURE_IBPB))
		set_static_key(&ibpb_enabled_key, enable);
}

/*
 * The following values are written to IBRS on kernel entry/exit:
 *
 *		entry	exit
 * ibrs		  1	 0
 * ibrs_always	  1	 x (not written on exit)
 * ibrs_user	  0	 1
 */

static void set_spec_ctrl_pcp_ibrs(void)
{
	set_spec_ctrl_pcp(true, false);
	set_spec_ctrl_ibpb(true);
	ibrs_mode = IBRS_ENABLED;
}

static void set_spec_ctrl_pcp_ibrs_always(void)
{
	set_spec_ctrl_pcp(true, true);
	set_spec_ctrl_ibpb(true);
	ibrs_mode = IBRS_ENABLED_ALWAYS;
}

static void set_spec_ctrl_pcp_ibrs_user(void)
{
	set_spec_ctrl_pcp(false, true);
	set_spec_ctrl_ibpb(true);
	ibrs_mode = IBRS_ENABLED_USER;
}

void clear_spec_ctrl_pcp(void)
{
	ibrs_mode = IBRS_DISABLED;
	set_spec_ctrl_pcp(false, false);
	if (!static_key_enabled(&retp_enabled_key))
		set_spec_ctrl_ibpb(false);
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

static void set_spec_ctrl_retp(bool enable)
{
	/*
	 * Make sure that IBPB is enabled if either IBRS or retpoline
	 * is enabled. ibrs_mode should be properly set before calling
	 * set_spec_ctrl_retp().
	 */
	set_static_key(&retp_enabled_key, enable);
	if (enable || (ibrs_mode == IBRS_DISABLED))
		set_spec_ctrl_ibpb(enable);
}

static void spec_ctrl_disable_all(void)
{
	int cpu;

	for_each_possible_cpu(cpu)
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.enabled, cpu), 0);

	set_spec_ctrl_retp(false);
	set_spec_ctrl_ibpb(false);
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

static bool is_skylake_era(void)
{
	if (boot_cpu_data.x86_vendor == X86_VENDOR_INTEL &&
	    boot_cpu_data.x86 == 6) {
		switch (boot_cpu_data.x86_model) {
		case INTEL_FAM6_SKYLAKE_MOBILE:
		case INTEL_FAM6_SKYLAKE_DESKTOP:
		case INTEL_FAM6_SKYLAKE_X:
		case INTEL_FAM6_KABYLAKE_MOBILE:
		case INTEL_FAM6_KABYLAKE_DESKTOP:
			return true;
		}
	}
	return false;
}

/*
 * The caller should have checked X86_FEATURE_IBRS_ENHANCED before calling
 * it, Which also implies X86_FEATURE_IBRS is present.
 */
void spec_ctrl_enable_ibrs_enhanced(void)
{
	ibrs_mode = IBRS_ENHANCED;
	set_spec_ctrl_pcp(true, true);
	set_spec_ctrl_ibpb(true);
}

bool spec_ctrl_force_enable_ibrs(void)
{
	if (cpu_has_spec_ctrl()) {
		if (boot_cpu_has(X86_FEATURE_IBRS_ENHANCED))
			spec_ctrl_enable_ibrs_enhanced();
		else
			set_spec_ctrl_pcp_ibrs();
		return true;
	}

	return false;
}

bool spec_ctrl_cond_enable_ibrs(bool full_retp)
{
	bool retbleed = boot_cpu_has_bug(X86_BUG_RETBLEED) &&
			boot_cpu_data.x86_vendor == X86_VENDOR_INTEL;

	if (cpu_has_spec_ctrl() &&
	    (retbleed || is_skylake_era() || !full_retp) && !noibrs_cmdline) {
		if (boot_cpu_has(X86_FEATURE_IBRS_ENHANCED)) {
			spec_ctrl_enable_ibrs_enhanced();
		} else {
			set_spec_ctrl_pcp_ibrs();
			/*
			 * Print a warning message about performance
			 * impact of enabling IBRS vs. retpoline.
			 */
			pr_warn_once("Using IBRS as the default Spectre v2 mitigation for a Skylake-\n");
			pr_warn_once("generation CPU.  This may have a negative performance impact.\n");
		}
		return true;
	}

	return false;
}

bool spec_ctrl_enable_ibrs_always(void)
{
	if (cpu_has_spec_ctrl()) {
		if (boot_cpu_has(X86_FEATURE_IBRS_ENHANCED))
			spec_ctrl_enable_ibrs_enhanced();
		else
			set_spec_ctrl_pcp_ibrs_always();
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
		return true;
	}

	ibp_disabled = false;
	return false;
}

bool spec_ctrl_cond_enable_ibp_disabled(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE) && !noibrs_cmdline) {
		ibp_disabled = true;
		return true;
	}

	ibp_disabled = false;
	return false;
}

void spec_ctrl_enable_retpoline(void)
{
	set_spec_ctrl_retp(true);
}

void spec_ctrl_enable_retpoline_amd(void)
{
	retpoline_amd_mode = true;
	setup_force_cpu_cap(X86_FEATURE_RETPOLINE_AMD);
	set_spec_ctrl_retp(true);
}

bool spec_ctrl_enable_retpoline_ibrs_user(void)
{
	if (!cpu_has_spec_ctrl())
		return false;

	if (boot_cpu_has(X86_FEATURE_IBRS_ENHANCED)) {
		spec_ctrl_enable_ibrs_enhanced();
		return true;
	}

	set_spec_ctrl_retp(true);
	set_spec_ctrl_pcp_ibrs_user();
	return true;
}

void spec_ctrl_report_unsafe_module(struct module *mod)
{
	if (retp_compiler() && !is_skylake_era())
		pr_warn_once("WARNING: module '%s' built without retpoline-enabled compiler, may affect Spectre v2 mitigation\n",
			     mod->name);

	unsafe_module = true;
}

enum spectre_v2_mitigation spec_ctrl_get_mitigation(void)
{
	enum spectre_v2_mitigation mode = SPECTRE_V2_NONE;

	if (ibp_disabled)
		mode = SPECTRE_V2_IBP_DISABLED;
	else if (ibrs_mode == IBRS_ENABLED_ALWAYS)
		mode = SPECTRE_V2_IBRS_ALWAYS;
	else if (ibrs_mode == IBRS_ENABLED)
		mode = SPECTRE_V2_IBRS;
	else if (ibrs_mode == IBRS_ENHANCED)
		mode = SPECTRE_V2_IBRS_ENHANCED;
	else if (retp_enabled()) {
		if (!retp_enabled_full())
			mode = SPECTRE_V2_RETPOLINE_MINIMAL;
		else if (!boot_cpu_has(X86_FEATURE_IBPB))
			mode = SPECTRE_V2_RETPOLINE_NO_IBPB;
		else if (unsafe_module)
			mode = SPECTRE_V2_RETPOLINE_UNSAFE_MODULE;
		else if (ibrs_mode == IBRS_ENABLED_USER)
			mode = SPECTRE_V2_RETPOLINE_IBRS_USER;
		else if (retpoline_amd_mode)
			mode = SPECTRE_V2_RETPOLINE_AMD;
		else
			mode = SPECTRE_V2_RETPOLINE;
	}

	spectre_v2_enabled = mode;	/* Update spectre_v2_enabled */
	return spectre_v2_enabled;
}

static void spec_ctrl_print_features(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		printk(KERN_INFO "FEATURE SPEC_CTRL Present (Implicit)\n");
		printk(KERN_INFO "FEATURE IBPB_SUPPORT Present (Implicit)\n");
		return;
	}

	if (boot_cpu_has(X86_FEATURE_IBRS))
		printk(KERN_INFO "FEATURE SPEC_CTRL Present\n");
	else
		printk(KERN_INFO "FEATURE SPEC_CTRL Not Present\n");

	if (boot_cpu_has(X86_FEATURE_IBPB))
		printk(KERN_INFO "FEATURE IBPB_SUPPORT Present\n");
	else
		printk(KERN_INFO "FEATURE IBPB_SUPPORT Not Present\n");
}

void spec_ctrl_cpu_init(void)
{
	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE)) {
		bool enabled = !ibp_disabled;
		__sync_this_cpu_ibp(&enabled);
		return;
	}

	if ((ibrs_mode == IBRS_ENABLED_ALWAYS) ||
	    (ibrs_mode == IBRS_ENHANCED) ||
	    (spec_ctrl_msr_write && (system_state == SYSTEM_BOOTING)))
		native_wrmsr(MSR_IA32_SPEC_CTRL,
			     this_cpu_read(spec_ctrl_pcp.entry),
			     this_cpu_read(spec_ctrl_pcp.hi32));
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
	set_static_key(&ibrs_present_key, boot_cpu_has(X86_FEATURE_IBRS));
	spec_ctrl_print_features();
}

void spec_ctrl_rescan_cpuid(void)
{
	enum spectre_v2_mitigation old_mode;
	bool old_ibrs, old_ibpb, old_ssbd, old_mds;
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
		old_mds  = boot_cpu_has(X86_FEATURE_MD_CLEAR);
		old_mode = spec_ctrl_get_mitigation();

		/* detect spec ctrl related cpuid additions */
		get_cpu_cap(&boot_cpu_data);

		/*
		 * If there were no spec ctrl or MDS related changes,
		 * we're done
		 */
		ssbd_changed = (old_ssbd != boot_cpu_has(X86_FEATURE_SSBD));
		if (old_ibrs == boot_cpu_has(X86_FEATURE_IBRS) &&
		    old_ibpb == boot_cpu_has(X86_FEATURE_IBPB) &&
		    old_mds  == boot_cpu_has(X86_FEATURE_MD_CLEAR) &&
		    !ssbd_changed)
			goto done;

		/*
		 * The IBRS, IBPB, SSBD & MDS cpuid bits may have
		 * just been set in the boot_cpu_data, transfer them
		 * to the per-cpu data too.
		 */
		if (boot_cpu_has(X86_FEATURE_IBRS))
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

		/* update static key, print the changed IBRS/IBPB features */
		spec_ctrl_init();

		if (ssbd_changed) {
			u64 old_spec_ctrl = x86_spec_ctrl_base;

			/*
			 * Redo speculative store bypass setup.
			 */
			ssb_select_mitigation();
			if (x86_spec_ctrl_base != old_spec_ctrl) {
				/*
				 * Need to propagate the new baseline to all
				 * the percpu spec_ctrl structures. The
				 * spectre v2 re-initialization below will
				 * reset to the right percpu values.
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
		if (old_mode != spec_ctrl_get_mitigation())
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
		this_cpu_or(spec_ctrl_pcp.entry, SPEC_CTRL_SSBD);
		this_cpu_or(spec_ctrl_pcp.exit,  SPEC_CTRL_SSBD);
	} else {
		this_cpu_and(spec_ctrl_pcp.entry, ~(int)SPEC_CTRL_SSBD);
		this_cpu_and(spec_ctrl_pcp.exit,  ~(int)SPEC_CTRL_SSBD);
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
		} else {
			WARN_ON(enable != IBRS_ENABLED_ALWAYS);
			sync_all_cpus_ibp(false);
			ibp_disabled = true;
			set_spec_ctrl_retp(false);
		}
		goto out_unlock;
	}

	if (!cpu_has_spec_ctrl()) {
		count = -ENODEV;
		goto out_unlock;
	}

	/*
	 * With enhanced IBRS, it is either IBRS_ENHANCED or IBRS_DISABLED.
	 * Other options are not supported.
	 */
	if (boot_cpu_has(X86_FEATURE_IBRS_ENHANCED) &&
	   (enable != IBRS_DISABLED) && (enable != IBRS_ENHANCED)) {
		count = -EINVAL;
		goto out_unlock;
	}
	if (!boot_cpu_has(X86_FEATURE_IBRS_ENHANCED) &&
	   (enable == IBRS_ENHANCED)) {
		count = -EINVAL;
		goto out_unlock;
	}

	if (enable == IBRS_DISABLED) {
		clear_spec_ctrl_pcp();
		sync_all_cpus_spec_ctrl();
	} else if (enable == IBRS_ENABLED) {
		set_spec_ctrl_pcp_ibrs();
		set_spec_ctrl_retp(false);
	} else if (enable == IBRS_ENABLED_ALWAYS) {
		set_spec_ctrl_pcp_ibrs_always();
		set_spec_ctrl_retp(false);
		sync_all_cpus_spec_ctrl();
	} else if (enable == IBRS_ENHANCED) {
		spec_ctrl_enable_ibrs_enhanced();
		set_spec_ctrl_retp(false);
		sync_all_cpus_spec_ctrl();
	} else {
		WARN_ON(enable != IBRS_ENABLED_USER);
		set_spec_ctrl_pcp_ibrs_user();
		set_spec_ctrl_retp(true);
	}
	spec_ctrl_get_mitigation();

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
	unsigned int enabled = retp_enabled();
	return __enabled_read(file, user_buf, count, ppos, &enabled);
}

#define RETP_IBRS_OFF_WARN "WARNING: disabling IBRS on a RETBleed affected CPU is not safe."
#define RETP_IBRS_ON_FAIL "WARNING: failed to set IBRS. CPU vulnerable to RETBleed attacks."

static ssize_t retp_enabled_write(struct file *file,
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

	if (enable > 2)
		return -EINVAL;

	mutex_lock(&spec_ctrl_mutex);

	if (!!enable == retp_enabled())
		goto out_unlock;

	if (enable) {
		bool force_enable = (enable == 2) ? true : false;

		/*
		 * RETBleed affected CPUs (Intel) depend on IBRS as
		 * an effective mitigation mechanism. We'll override
		 * retp_enabled=1 with spectre_v2=ibrs here.
		 */
		if (boot_cpu_has_bug(X86_BUG_RETBLEED) &&
		    boot_cpu_data.x86_vendor == X86_VENDOR_INTEL) {
			if (!force_enable) {
				if (ibrs_mode == IBRS_DISABLED) {
					pr_warn("%s Switching to spectre_v2=ibrs\n",
						RETP_IBRS_OFF_WARN);

					if (spec_ctrl_cond_enable_ibrs(true))
						goto out_get_mitigation;
					else
						pr_warn("%s\n", RETP_IBRS_ON_FAIL);
				}

				goto out_unlock;
			}

			/*
			 * retp_enabled=2 case here, which preserves the
			 * old behavior and disables IBRS.
			 * on a RETBleed affected CPU we just throw the
			 * warning and keep on going.
			 */
			pr_warn("%s\n", RETP_IBRS_OFF_WARN);
		}

		/* enforce sane combinations */
		if (ibp_disabled) {
			sync_all_cpus_ibp(true);
			ibp_disabled = false;
		} else if ((ibrs_mode == IBRS_ENABLED) ||
			   (ibrs_mode == IBRS_ENHANCED)) {
			clear_spec_ctrl_pcp();
			sync_all_cpus_spec_ctrl();
		} else if (ibrs_mode == IBRS_ENABLED_ALWAYS) {
			set_spec_ctrl_pcp_ibrs_user();
		}
	}

	set_spec_ctrl_retp(!!enable);

out_get_mitigation:
	spec_ctrl_get_mitigation();

out_unlock:
	mutex_unlock(&spec_ctrl_mutex);
	return count;
}


static const struct file_operations fops_retp_enabled = {
	.read = retp_enabled_read,
	.write = retp_enabled_write,
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
		smp_store_mb(ssb_mode, mode);

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
		case IBRS_ENHANCED:
			spec_ctrl_enable_ibrs_enhanced();
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
		smp_store_mb(ssb_mode, mode);

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

	WARN_ON_ONCE(ssb_is_user_settable(ssb_mode) !=
		     static_key_enabled(&ssbd_userset_key));

	/*
	 * User settable  => !settable: clear ssbd_userset_key early
	 * User !settable => settable : set ssbd_userset_key late
	 */
	if (static_key_enabled(&ssbd_userset_key) &&
	   !ssb_is_user_settable(mode))
		static_key_slow_dec(&ssbd_userset_key);

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
	if (!static_key_enabled(&ssbd_userset_key) && ssb_is_user_settable(mode))
		static_key_slow_inc(&ssbd_userset_key);
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
	unsigned int present = atomic_read(&sched_smt_present.enabled);

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
	debugfs_create_file("retp_enabled", S_IRUSR | S_IWUSR,
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
