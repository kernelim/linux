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
 * SPEC_CTRL MSR bits being managed by the kernel.
 */
#define SPEC_CTRL_MANAGED_MASK	(FEATURE_ENABLE_IBRS|FEATURE_ENABLE_SSBD)

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
 * x86_amd_ls_cfg_rds_mask is initialized in identify_boot_cpu().
 */
u64 __read_mostly x86_amd_ls_cfg_base;
u64 __read_mostly x86_amd_ls_cfg_rds_mask;

void spec_ctrl_save_msr(void)
{
	int cpu;
	unsigned int hival, loval;
	static int savecnt;

	spec_ctrl_msr_write = false;

	/*
	 * Read the SPEC_CTRL MSR to account for reserved bits which may have
	 * unknown values. AMD64_LS_CFG MSR is cached in the early AMD
	 * init code as it is not enumerated and depends on the family.
	 */
	if (boot_cpu_has(X86_FEATURE_IBRS) && !savecnt) {
		/*
		 * This part is run only the first time it is called.
		 */
		rdmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
		if (x86_spec_ctrl_base & SPEC_CTRL_MANAGED_MASK) {
			x86_spec_ctrl_base &= ~SPEC_CTRL_MANAGED_MASK;
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
 * RHEL note:
 * Upstream has implemented the following APIs for getting and setting
 * the SPEC_CTRL MSR value.
 *
 *  - void x86_spec_ctrl_set(u64 val)
 *  - u64 x86_spec_ctrl_get_default(void)
 *
 * We don't use it directly since we have a lot of IBRS management code
 * that touches SPEC_CTRL directly.
 */

static void set_spec_ctrl_pcp(bool entry, bool exit)
{
	unsigned int enabled   = percpu_read(spec_ctrl_pcp.enabled);
	unsigned int entry_val = percpu_read(spec_ctrl_pcp.entry);
	unsigned int exit_val  = percpu_read(spec_ctrl_pcp.exit);
	int cpu;

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
		entry_val |= FEATURE_ENABLE_IBRS;
	else
		entry_val &= ~FEATURE_ENABLE_IBRS;

	if (exit)
		exit_val |= FEATURE_ENABLE_IBRS;
	else
		exit_val &= ~FEATURE_ENABLE_IBRS;

	for_each_possible_cpu(cpu) {
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.enabled, cpu), enabled);
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.entry, cpu), entry_val);
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.exit, cpu), exit_val);
	}
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

static void spec_ctrl_sync_all_cpus(u32 msr_nr, u64 val)
{
	int cpu;
	get_online_cpus();
	for_each_online_cpu(cpu)
		wrmsrl_on_cpu(cpu, msr_nr, val);
	put_online_cpus();
}

static void sync_all_cpus_ibrs(bool enable)
{
	spec_ctrl_sync_all_cpus(MSR_IA32_SPEC_CTRL,
				 enable ? (x86_spec_ctrl_base | FEATURE_ENABLE_IBRS)
					: x86_spec_ctrl_base);
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

	if (ibrs_mode == IBRS_ENABLED_ALWAYS)
		sync_all_cpus_ibrs(true);
	else if (ibrs_mode == IBRS_DISABLED)
		sync_all_cpus_ibrs(false);
}

void spec_ctrl_init(void)
{
	spec_ctrl_print_features();

	/*
	 * If the x86_spec_ctrl_base is modified, propagate it to the
	 * percpu spec_ctrl structure as well as forcing MSR write.
	 */
	if (x86_spec_ctrl_base) {
		wrmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
		spec_ctrl_save_msr();
		spec_ctrl_msr_write = true;
	}
}

void spec_ctrl_rescan_cpuid(void)
{
	enum spectre_v2_mitigation old_mode;
	bool old_ibrs, old_ibpb, old_ssbd;
	bool ssbd_changed;
	int cpu;

	if (boot_cpu_has(X86_FEATURE_IBP_DISABLE))
		return;

	mutex_lock(&spec_ctrl_mutex);
	if (boot_cpu_data.x86_vendor == X86_VENDOR_INTEL ||
	    boot_cpu_data.x86_vendor == X86_VENDOR_AMD) {
		bool amd_ssbd = boot_cpu_has(X86_FEATURE_AMD_SSBD);

		old_ibrs = boot_cpu_has(X86_FEATURE_IBRS);
		old_ibpb = boot_cpu_has(X86_FEATURE_IBPB);
		old_ssbd = boot_cpu_has(X86_FEATURE_SSBD);
		old_mode = spectre_v2_get_mitigation();

		/* detect spec ctrl related cpuid additions */
		get_cpu_cap(&boot_cpu_data);

		/*
		 * For AMD family 0x15-0x17, the SSBD bit is specially
		 * hard-coded. Hence, a call to get_cpu_cap() will clear
		 * the SSBD bit as it is part of an architectural leaf.
		 * The Linux internal AMD_SSBD bit may not be cleared.
		 * We need to detect this situation and correct it.
		 */
		if (amd_ssbd && !boot_cpu_has(X86_FEATURE_SSBD)) {
			setup_force_cpu_cap(X86_FEATURE_SSBD);
			setup_force_cpu_cap(X86_FEATURE_AMD_SSBD);
		}

		/* if there were no spec ctrl related changes, we're done */
		ssbd_changed = (old_ssbd != boot_cpu_has(X86_FEATURE_SSBD));
		if (old_ibrs == boot_cpu_has(X86_FEATURE_IBRS) &&
		    old_ibpb == boot_cpu_has(X86_FEATURE_IBPB) && !ssbd_changed)
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
				sync_all_cpus_ibrs(false);
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
	}
done:
	mutex_unlock(&spec_ctrl_mutex);
}
EXPORT_SYMBOL_GPL(spec_ctrl_rescan_cpuid);

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
		sync_all_cpus_ibrs(false);
		spectre_v2_retpoline_reset();
	} else if (enable == IBRS_ENABLED) {
		set_spec_ctrl_pcp_ibrs();
		spectre_v2_set_mitigation(SPECTRE_V2_IBRS);
	} else if (enable == IBRS_ENABLED_ALWAYS) {
		set_spec_ctrl_pcp_ibrs_always();
		sync_all_cpus_ibrs(true);
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

static int __init debugfs_spec_ctrl(void)
{
	debugfs_create_file("ibrs_enabled", S_IRUSR | S_IWUSR,
			    arch_debugfs_dir, NULL, &fops_ibrs_enabled);
	debugfs_create_file("ibpb_enabled", S_IRUSR,
			    arch_debugfs_dir, NULL, &fops_ibpb_enabled);
	debugfs_create_file("retp_enabled", S_IRUSR,
			    arch_debugfs_dir, NULL, &fops_retp_enabled);

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
