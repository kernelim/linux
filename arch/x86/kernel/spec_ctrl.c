/*
 *  Copyright (C) 2018  Red Hat, Inc.
 *
 *  This work is licensed under the terms of the GNU GPL, version 2. See
 *  the COPYING file in the top-level directory.
 */

#include <linux/cpu.h>
#include <linux/percpu.h>
#include <linux/uaccess.h>
#include <asm/spec_ctrl.h>
#include <asm/cpufeature.h>
#include <asm/nospec-branch.h>
#include <asm/intel-family.h>
#include <asm/cpu.h>

/*
 * Task specific SPEC_CTRL feature bits - SSBD and STIBP
 */
#define SPEC_CTRL_TASK_MASK	(SPEC_CTRL_SSBD | SPEC_CTRL_STIBP)

/*
 * Kernel IBRS speculation control structure
 */
DEFINE_PER_CPU(struct kernel_ibrs_spec_ctrl, spec_ctrl_pcp);

static bool __initdata noibrs_cmdline;
unsigned int ibrs_mode __read_mostly;

static void set_spec_ctrl_pcp(bool entry, bool exit)
{
	unsigned int hi32_val, entry_val, exit_val;
	int cpu;

	/*
	 * For ibrs_always, we only need to write the MSR at kernel entry
	 * to fulfill the barrier semantics for some CPUs.
	 */
	if (entry && exit) {
		setup_force_cpu_cap(X86_FEATURE_SPEC_CTRL_ENTRY);
	} else {
		setup_force_cpu_cap(X86_FEATURE_SPEC_CTRL_ENTRY);
		setup_force_cpu_cap(X86_FEATURE_SPEC_CTRL_EXIT);
	}

	/*
	 * The x86_spec_ctrl_base is set to the state of SPEC_CTRL MSR
	 * in kernel mode. STIBP will be masked off if IBRS is set.
	 */
	if (exit) {
		exit_val = (unsigned int)x86_spec_ctrl_base | SPEC_CTRL_IBRS;
		exit_val &= ~SPEC_CTRL_STIBP;
	} else {
		exit_val = (unsigned int)x86_spec_ctrl_base & ~SPEC_CTRL_IBRS;
	}

	if (entry) {
		x86_spec_ctrl_base |= SPEC_CTRL_IBRS;
		x86_spec_ctrl_base &= ~SPEC_CTRL_STIBP;
	}

	hi32_val  = (unsigned int)(x86_spec_ctrl_base >> 32);
	entry_val = (unsigned int)x86_spec_ctrl_base;

	for_each_possible_cpu(cpu) {
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.hi32, cpu), hi32_val);
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.entry, cpu), entry_val);
		WRITE_ONCE(per_cpu(spec_ctrl_pcp.exit, cpu), exit_val);
	}
}

/*
 * The following values are written to IBRS on kernel entry/exit:
 *
 *		entry	exit
 * ibrs		  1	 0
 * ibrs_always	  1	 1
 * ibrs_user	  0	 1
 */

static inline void set_spec_ctrl_pcp_ibrs(void)
{
	set_spec_ctrl_pcp(true, false);
	ibrs_mode = IBRS_ENABLED;
}

static inline void set_spec_ctrl_pcp_ibrs_always(void)
{
	set_spec_ctrl_pcp(true, true);
	ibrs_mode = IBRS_ENABLED_ALWAYS;
}

static inline void set_spec_ctrl_pcp_ibrs_user(void)
{
	set_spec_ctrl_pcp(false, true);
	ibrs_mode = IBRS_ENABLED_USER;
}

bool __init spec_ctrl_enable_ibrs(void)
{
	if (cpu_has_ibrs() && !noibrs_cmdline) {
		set_spec_ctrl_pcp_ibrs();
		return true;
	}

	return false;
}

bool __init spec_ctrl_enable_ibrs_always(void)
{
	if (cpu_has_ibrs() && !noibrs_cmdline) {
		set_spec_ctrl_pcp_ibrs_always();
		/*
		 * Make sure the boot CPU has IBRS bit set.
		 */
		spec_ctrl_cpu_init();
		return true;
	}

	return false;
}

bool __init spec_ctrl_enable_retpoline_ibrs_user(void)
{
	if (!cpu_has_ibrs() || noibrs_cmdline)
		return false;

	set_spec_ctrl_pcp_ibrs_user();
	return true;
}

static int __init noibrs(char *str)
{
	noibrs_cmdline = true;

	return 0;
}
early_param("noibrs", noibrs);

static __init void spec_ctrl_print_features(void)
{
	if (boot_cpu_has(X86_FEATURE_IBRS))
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
	if (ibrs_mode == IBRS_ENABLED_ALWAYS)
		native_wrmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
}

void __init spec_ctrl_init(void)
{
	spec_ctrl_print_features();
}

/* Check for Skylake-like CPUs */
bool is_skylake_era(void)
{
	if (boot_cpu_data.x86_vendor == X86_VENDOR_INTEL &&
	    boot_cpu_data.x86 == 6) {
		switch (boot_cpu_data.x86_model) {
		case INTEL_FAM6_SKYLAKE_L:
		case INTEL_FAM6_SKYLAKE:
		case INTEL_FAM6_SKYLAKE_X:
		case INTEL_FAM6_KABYLAKE_L:
		case INTEL_FAM6_KABYLAKE:
			return true;
		}
	}
	return false;
}

/*
 * Both the SSBD and the STIBP bits in the SPEC_CTRL MSR of the current
 * CPU may be managed on a per task basis.
 *
 * This function will only be called when IBRS is enabled in either the
 * kernel and/or the userland. With IBRS enabled, we don't need STIBP as
 * it may have a pretty big performance impact. So the STIBP bit will be
 * mask out if IBRS is enabled. The STIBP bit comes from either the given
 * SPEC_CTRL MSR value (switch_to_cond_stibp true) or from x86_spec_ctrl_base.
 */
void spec_ctrl_update(u64 spec_ctrl)
{
	u64 newval;
	u64 entry = this_cpu_read(spec_ctrl_pcp.entry);
	u64 exit  = this_cpu_read(spec_ctrl_pcp.exit);
	u64 stibp = static_branch_likely(&switch_to_cond_stibp)
		  ? (spec_ctrl & SPEC_CTRL_STIBP)
		  : (x86_spec_ctrl_base & SPEC_CTRL_STIBP);

	newval = (entry & ~SPEC_CTRL_TASK_MASK) | (spec_ctrl & SPEC_CTRL_SSBD) |
		 ((entry & SPEC_CTRL_IBRS) ? 0 : stibp);
	if (newval != entry)
		this_cpu_write(spec_ctrl_pcp.entry, newval);

	newval = (exit & ~SPEC_CTRL_TASK_MASK) | (spec_ctrl & SPEC_CTRL_SSBD) |
		 ((exit & SPEC_CTRL_IBRS) ? 0 : stibp);
	if (newval != exit)
		this_cpu_write(spec_ctrl_pcp.exit, newval);
}

/*
 * Only the SPEC_CTRL_STIBP bit may be set in enable_stibp.
 */
static inline void atomic_update_stibp_pcp(atomic_t *pval,
					   unsigned int enable_stibp)
{
	int val = atomic_read(pval);

	/* Don't turn on STIBP if IBRS has been set */
	if (val & SPEC_CTRL_IBRS)
		enable_stibp = 0;

	if (!(enable_stibp ^ (val & SPEC_CTRL_STIBP)))
		return;
	if (enable_stibp)
		atomic_or(SPEC_CTRL_STIBP, pval);
	else
		atomic_and((int)~SPEC_CTRL_STIBP, pval);
}

/*
 * Synchronize the strict STIBP state in x86_spec_ctrl_base with those in
 * the percpu spec_ctrl_pcp when the SMT state changes.
 */
void spec_ctrl_smt_update(void)
{
	unsigned int cpu, enable_stibp;
	int idx;

	if (!boot_cpu_has(X86_FEATURE_STIBP) || (ibrs_mode == IBRS_DISABLED))
		return;

	enable_stibp = x86_spec_ctrl_base & SPEC_CTRL_STIBP;
	if ((this_cpu_read(spec_ctrl_pcp.entry) & SPEC_CTRL_STIBP)
			== enable_stibp)
		goto check_ibrs;	/* No state change */

	/*
	 * This is a slowpath. Atomic instructions are used to update the
	 * percpu spec_ctrl_pcp. However, concurrent update by
	 * spec_ctrl_update() above may cause the change to be lost if
	 * that happens to be in the middle of its read-modify-write cycle.
	 * So we double-check it one more time to be sure.
	 */
	for (idx = 0; idx < 2; idx++) {
		for_each_possible_cpu(cpu) {
			struct kernel_ibrs_spec_ctrl *pcp =
					per_cpu_ptr(&spec_ctrl_pcp, cpu);

			/*
			 * If IBRS is enabled, we don't need to turn on STIBP.
			 */
			if (!(pcp->entry & SPEC_CTRL_IBRS))
				atomic_update_stibp_pcp((atomic_t *)&pcp->entry,
							enable_stibp);
			if (!(pcp->exit & SPEC_CTRL_IBRS))
				atomic_update_stibp_pcp((atomic_t *)&pcp->exit,
							enable_stibp);
		}
	}

	/*
	 * Mask off STIBP in x86_spec_ctrl_base if IBRS is on.
	 */
check_ibrs:
	if (enable_stibp && (x86_spec_ctrl_base & SPEC_CTRL_IBRS))
		x86_spec_ctrl_base &= ~SPEC_CTRL_STIBP;
}
