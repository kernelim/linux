/*
 *  Copyright (C) 1994  Linus Torvalds
 *
 *  Cyrix stuff, June 1998 by:
 *	- Rafael R. Reilova (moved everything from head.S),
 *        <rreilova@ececs.uc.edu>
 *	- Channing Corn (tests & fixes),
 *	- Andrew D. Balsa (code cleanup).
 */
#include <linux/init.h>
#include <linux/utsname.h>
#include <linux/cpu.h>

#include <asm/nospec-branch.h>
#include <asm/cmdline.h>
#include <asm/bugs.h>
#include <asm/processor.h>
#include <asm/processor-flags.h>
#include <asm/i387.h>
#include <asm/msr.h>
#include <asm/vmx.h>
#include <asm/paravirt.h>
#include <asm/alternative.h>
#include <asm/pgtable.h>
#include <asm/cacheflush.h>
#include <asm/spec_ctrl.h>
#include <asm/hypervisor.h>
#include <asm/intel-family.h>
#include <linux/prctl.h>
#include <linux/sched/smt.h>

#include "cpu.h"

static void __init spectre_v1_select_mitigation(void);
static void __init retbleed_select_mitigation(void);
static void __init spectre_v2_select_mitigation(void);
static void __init ssb_parse_cmdline(void);
void ssb_select_mitigation(void);
static void __init l1tf_select_mitigation(void);
static void __init mds_select_mitigation(void);
static void __init md_clear_update_mitigation(void);
static void __init md_clear_select_mitigation(void);
static void __init taa_select_mitigation(void);
static void __init mmio_select_mitigation(void);
static void __init srbds_select_mitigation(void);

extern void spec_ctrl_save_msr(void);

static DEFINE_MUTEX(spec_ctrl_mutex);

/* Control MDS CPU buffer clear before returning to user space */
struct static_key mds_user_clear = STATIC_KEY_INIT_FALSE;
EXPORT_SYMBOL_GPL(mds_user_clear);
/* Control MDS CPU buffer clear before idling (halt, mwait) */
struct static_key mds_idle_clear = STATIC_KEY_INIT_FALSE;
EXPORT_SYMBOL_GPL(mds_idle_clear);
/* Controls CPU Fill buffer clear before KVM guest MMIO accesses */
struct static_key mmio_stale_data_clear = STATIC_KEY_INIT_FALSE;
EXPORT_SYMBOL_GPL(mmio_stale_data_clear);

void __init check_bugs(void)
{
	identify_boot_cpu();

	spec_ctrl_save_msr();

	/*
	 * identify_boot_cpu() initialized SMT support information, let the
	 * core code know.
	 */
	cpu_smt_check_topology();

	if (!IS_ENABLED(CONFIG_SMP)) {
		pr_info("CPU: ");
		print_cpu_info(&boot_cpu_data);
	}

	/*
	 * Select proper mitigation for any exposure to the Speculative Store
	 * Bypass vulnerability (exposed as a bug in "Memory Disambiguation")
	 * This has to be done before spec_ctrl_init() to make sure that its
	 * SPEC_CTRL MSR value is properly set up.
	 */
	ssb_parse_cmdline();

	spec_ctrl_init();

	/* Select the proper CPU mitigations before patching alternatives */
	spectre_v1_select_mitigation();
	spectre_v2_select_mitigation();
	retbleed_select_mitigation();
	spec_ctrl_cpu_init();
	ssb_select_mitigation();
	l1tf_select_mitigation();
	md_clear_select_mitigation();
	srbds_select_mitigation();

	arch_smt_update();

#ifdef CONFIG_X86_32
	/*
	 * Check whether we are able to run this kernel safely on SMP.
	 *
	 * - i386 is no longer supported.
	 * - In order to run on anything without a TSC, we need to be
	 *   compiled for a i486.
	 */
	if (boot_cpu_data.x86 < 4)
		panic("Kernel requires i486+ for 'invlpg' and other features");

	init_utsname()->machine[1] =
		'0' + (boot_cpu_data.x86 > 6 ? 6 : boot_cpu_data.x86);
	alternative_instructions();

	/*
	 * kernel_fpu_begin/end() in check_fpu() relies on the patched
	 * alternative instructions.
	 */
	check_fpu();
#else /* CONFIG_X86_64 */
	alternative_instructions();

	/*
	 * Make sure the first 2MB area is not mapped by huge pages
	 * There are typically fixed size MTRRs in there and overlapping
	 * MTRRs into large pages causes slow downs.
	 *
	 * Right now we don't do that with gbpages because there seems
	 * very little benefit for that case.
	 */
	if (!direct_gbpages)
		set_memory_4k((unsigned long)__va(0), 1);
#endif
}

void x86_amd_ssbd_enable(void)
{
	u64 msrval = x86_amd_ls_cfg_base | x86_amd_ls_cfg_ssbd_mask;

	if (boot_cpu_has(X86_FEATURE_VIRT_SSBD))
		wrmsrl(MSR_AMD64_VIRT_SPEC_CTRL, SPEC_CTRL_SSBD);
	else if (boot_cpu_has(X86_FEATURE_LS_CFG_SSBD))
		wrmsrl(MSR_AMD64_LS_CFG, msrval);
}

/* The kernel command line selection */
enum spectre_v2_mitigation_cmd {
	SPECTRE_V2_CMD_NONE,
	SPECTRE_V2_CMD_FORCE,
	SPECTRE_V2_CMD_AUTO,
	SPECTRE_V2_CMD_RETPOLINE,
	SPECTRE_V2_CMD_RETPOLINE_AMD,
	SPECTRE_V2_CMD_RETPOLINE_FORCE,
	SPECTRE_V2_CMD_RETPOLINE_IBRS_USER,
	SPECTRE_V2_CMD_IBRS,
	SPECTRE_V2_CMD_IBRS_ALWAYS,
};

static const char *spectre_v2_strings[] = {
	[SPECTRE_V2_NONE]			= "Vulnerable",
	[SPECTRE_V2_RETPOLINE_MINIMAL]		= "Vulnerable: Minimal ASM retpoline",
	[SPECTRE_V2_RETPOLINE_NO_IBPB]		= "Vulnerable: Retpoline without IBPB",
	[SPECTRE_V2_RETPOLINE_UNSAFE_MODULE]	= "Vulnerable: Retpoline with unsafe module(s)",
	[SPECTRE_V2_RETPOLINE_AMD]		= "Vulnerable: AMD retpoline (LFENCE/JMP)",
	[SPECTRE_V2_RETPOLINE]			= "Mitigation: Full retpoline",
	[SPECTRE_V2_RETPOLINE_IBRS_USER]	= "Mitigation: Full retpoline and IBRS (user space)",
	[SPECTRE_V2_IBRS]			= "Mitigation: IBRS (kernel)",
	[SPECTRE_V2_IBRS_ALWAYS]		= "Mitigation: IBRS (kernel and user space)",
	[SPECTRE_V2_IBP_DISABLED]		= "Mitigation: IBP disabled",
	[SPECTRE_V2_IBRS_ENHANCED]		= "Mitigation: Enhanced IBRS",
};

enum spectre_v2_mitigation_cmd spectre_v2_cmd = SPECTRE_V2_CMD_AUTO;

#undef pr_fmt
#define pr_fmt(fmt)	"MDS: " fmt

/* Default mitigation for MDS-affected CPUs */
enum mds_mitigations mds_mitigation = MDS_MITIGATION_FULL;
static bool mds_nosmt = false;

static const char * const mds_strings[] = {
	[MDS_MITIGATION_OFF]	= "Vulnerable",
	[MDS_MITIGATION_FULL]	= "Mitigation: Clear CPU buffers",
	[MDS_MITIGATION_VMWERV]	= "Vulnerable: Clear CPU buffers attempted, no microcode",
};

static void __init mds_select_mitigation(void)
{
	if (!boot_cpu_has_bug(X86_BUG_MDS) || cpu_mitigations_off()) {
		mds_mitigation = MDS_MITIGATION_OFF;
		return;
	}

	if (mds_mitigation == MDS_MITIGATION_FULL) {
		if (!boot_cpu_has(X86_FEATURE_MD_CLEAR))
			mds_mitigation = MDS_MITIGATION_VMWERV;

		static_key_slow_inc(&mds_user_clear);

		if (!boot_cpu_has(X86_BUG_MSBDS_ONLY) &&
		    (mds_nosmt || cpu_mitigations_auto_nosmt()))
			cpu_smt_disable(false);
	}
}

void mds_print_mitigation(void)
{
	if (!boot_cpu_has_bug(X86_BUG_MDS) || cpu_mitigations_off())
		return;

	pr_info("%s\n", mds_strings[mds_mitigation]);
}

static int __init mds_cmdline(char *str)
{
	if (!boot_cpu_has_bug(X86_BUG_MDS))
		return 0;

	if (!str)
		return -EINVAL;

	if (!strcmp(str, "off"))
		mds_mitigation = MDS_MITIGATION_OFF;
	else if (!strcmp(str, "full"))
		mds_mitigation = MDS_MITIGATION_FULL;
	else if (!strcmp(str, "full,nosmt")) {
		mds_mitigation = MDS_MITIGATION_FULL;
		mds_nosmt = true;
	}

	return 0;
}
early_param("mds", mds_cmdline);

#undef pr_fmt
#define pr_fmt(fmt)	"TAA: " fmt

/* Default mitigation for TAA-affected CPUs */
static enum taa_mitigations taa_mitigation __read_mostly = TAA_MITIGATION_VERW;
static bool taa_nosmt __read_mostly;

static const char * const taa_strings[] = {
	[TAA_MITIGATION_OFF]		= "Vulnerable",
	[TAA_MITIGATION_UCODE_NEEDED]	= "Vulnerable: Clear CPU buffers attempted, no microcode",
	[TAA_MITIGATION_VERW]		= "Mitigation: Clear CPU buffers",
	[TAA_MITIGATION_TSX_DISABLED]	= "Mitigation: TSX disabled",
};

static void __init taa_select_mitigation(void)
{
	u64 ia32_cap;

	if (!boot_cpu_has_bug(X86_BUG_TAA)) {
		taa_mitigation = TAA_MITIGATION_OFF;
		return;
	}

	/* TSX previously disabled by tsx=off */
	if (!boot_cpu_has(X86_FEATURE_RTM)) {
		taa_mitigation = TAA_MITIGATION_TSX_DISABLED;
		return;
	}

	if (cpu_mitigations_off()) {
		taa_mitigation = TAA_MITIGATION_OFF;
		return;
	}

	/*
	 * TAA mitigation via VERW is turned off if both
	 * tsx_async_abort=off and mds=off are specified.
	 */
	if (taa_mitigation == TAA_MITIGATION_OFF &&
	    mds_mitigation == MDS_MITIGATION_OFF)
		return;

	if (boot_cpu_has(X86_FEATURE_MD_CLEAR))
		taa_mitigation = TAA_MITIGATION_VERW;
	else
		taa_mitigation = TAA_MITIGATION_UCODE_NEEDED;

	/*
	 * VERW doesn't clear the CPU buffers when MD_CLEAR=1 and MDS_NO=1.
	 * A microcode update fixes this behavior to clear CPU buffers. It also
	 * adds support for MSR_IA32_TSX_CTRL which is enumerated by the
	 * ARCH_CAP_TSX_CTRL_MSR bit.
	 *
	 * On MDS_NO=1 CPUs if ARCH_CAP_TSX_CTRL_MSR is not set, microcode
	 * update is required.
	 */
	ia32_cap = x86_read_arch_cap_msr();
	if ( (ia32_cap & ARCH_CAP_MDS_NO) &&
	    !(ia32_cap & ARCH_CAP_TSX_CTRL_MSR))
		taa_mitigation = TAA_MITIGATION_UCODE_NEEDED;

	/*
	 * TSX is enabled, select alternate mitigation for TAA which is
	 * the same as MDS. Enable MDS static branch to clear CPU buffers.
	 *
	 * For guests that can't determine whether the correct microcode is
	 * present on host, enable the mitigation for UCODE_NEEDED as well.
	 */
	static_key_slow_inc(&mds_user_clear);

	if (taa_nosmt || cpu_mitigations_auto_nosmt())
		cpu_smt_disable(false);
}

static int __init tsx_async_abort_parse_cmdline(char *str)
{
	if (!boot_cpu_has_bug(X86_BUG_TAA))
		return 0;

	if (!str)
		return -EINVAL;

	if (!strcmp(str, "off")) {
		taa_mitigation = TAA_MITIGATION_OFF;
	} else if (!strcmp(str, "full")) {
		taa_mitigation = TAA_MITIGATION_VERW;
	} else if (!strcmp(str, "full,nosmt")) {
		taa_mitigation = TAA_MITIGATION_VERW;
		taa_nosmt = true;
	}

	return 0;
}
early_param("tsx_async_abort", tsx_async_abort_parse_cmdline);

#undef pr_fmt
#define pr_fmt(fmt)	"MMIO Stale Data: " fmt

enum mmio_mitigations {
	MMIO_MITIGATION_OFF,
	MMIO_MITIGATION_UCODE_NEEDED,
	MMIO_MITIGATION_VERW,
};

/* Default mitigation for Processor MMIO Stale Data vulnerabilities */
static enum mmio_mitigations mmio_mitigation __read_mostly = MMIO_MITIGATION_VERW;
static bool mmio_nosmt __read_mostly = false;

static const char * const mmio_strings[] = {
	[MMIO_MITIGATION_OFF]		= "Vulnerable",
	[MMIO_MITIGATION_UCODE_NEEDED]	= "Vulnerable: Clear CPU buffers attempted, no microcode",
	[MMIO_MITIGATION_VERW]		= "Mitigation: Clear CPU buffers",
};

static void __init mmio_select_mitigation(void)
{
	u64 ia32_cap;

	if (!boot_cpu_has_bug(X86_BUG_MMIO_STALE_DATA) ||
	    cpu_mitigations_off()) {
		mmio_mitigation = MMIO_MITIGATION_OFF;
		return;
	}

	if (mmio_mitigation == MMIO_MITIGATION_OFF)
		return;

	ia32_cap = x86_read_arch_cap_msr();

	/*
	 * Enable CPU buffer clear mitigation for host and VMM, if also affected
	 * by MDS or TAA. Otherwise, enable mitigation for VMM only.
	 */
	if (boot_cpu_has_bug(X86_BUG_MDS) || (boot_cpu_has_bug(X86_BUG_TAA) &&
					      boot_cpu_has(X86_FEATURE_RTM)))
		static_key_slow_inc(&mds_user_clear);
	else
		static_key_slow_inc(&mmio_stale_data_clear);

	/*
	 * If Processor-MMIO-Stale-Data bug is present and Fill Buffer data can
	 * be propagated to uncore buffers, clearing the Fill buffers on idle
	 * is required irrespective of SMT state.
	 */
	if (!(ia32_cap & ARCH_CAP_FBSDP_NO))
		static_key_slow_inc(&mds_idle_clear);

	/*
	 * Check if the system has the right microcode.
	 *
	 * CPU Fill buffer clear mitigation is enumerated by either an explicit
	 * FB_CLEAR or by the presence of both MD_CLEAR and L1D_FLUSH on MDS
	 * affected systems.
	 */
	if ((ia32_cap & ARCH_CAP_FB_CLEAR) ||
	    (boot_cpu_has(X86_FEATURE_MD_CLEAR) &&
	     boot_cpu_has(X86_FEATURE_FLUSH_L1D) &&
	     !(ia32_cap & ARCH_CAP_MDS_NO)))
		mmio_mitigation = MMIO_MITIGATION_VERW;
	else
		mmio_mitigation = MMIO_MITIGATION_UCODE_NEEDED;

	if (mmio_nosmt || cpu_mitigations_auto_nosmt())
		cpu_smt_disable(false);
}

static int __init mmio_stale_data_parse_cmdline(char *str)
{
	if (!boot_cpu_has_bug(X86_BUG_MMIO_STALE_DATA))
		return 0;

	if (!str)
		return -EINVAL;

	if (!strcmp(str, "off")) {
		mmio_mitigation = MMIO_MITIGATION_OFF;
	} else if (!strcmp(str, "full")) {
		mmio_mitigation = MMIO_MITIGATION_VERW;
	} else if (!strcmp(str, "full,nosmt")) {
		mmio_mitigation = MMIO_MITIGATION_VERW;
		mmio_nosmt = true;
	}

	return 0;
}
early_param("mmio_stale_data", mmio_stale_data_parse_cmdline);

#undef pr_fmt
#define pr_fmt(fmt)     "" fmt

static void __init md_clear_update_mitigation(void)
{
	if (cpu_mitigations_off())
		return;

	if (!static_key_enabled(&mds_user_clear))
		goto out;

	/*
	 * mds_user_clear is now enabled. Update MDS, TAA and MMIO Stale Data
	 * mitigation, if necessary.
	 */
	if (mds_mitigation == MDS_MITIGATION_OFF &&
	    boot_cpu_has_bug(X86_BUG_MDS)) {
		mds_mitigation = MDS_MITIGATION_FULL;
		mds_select_mitigation();
	}
	if (taa_mitigation == TAA_MITIGATION_OFF &&
	    boot_cpu_has_bug(X86_BUG_TAA)) {
		taa_mitigation = TAA_MITIGATION_VERW;
		taa_select_mitigation();
	}
	if (mmio_mitigation == MMIO_MITIGATION_OFF &&
	    boot_cpu_has_bug(X86_BUG_MMIO_STALE_DATA)) {
		mmio_mitigation = MMIO_MITIGATION_VERW;
		mmio_select_mitigation();
	}
out:
	if (boot_cpu_has_bug(X86_BUG_MDS))
		pr_info("MDS: %s\n", mds_strings[mds_mitigation]);
	if (boot_cpu_has_bug(X86_BUG_TAA))
		pr_info("TAA: %s\n", taa_strings[taa_mitigation]);
	if (boot_cpu_has_bug(X86_BUG_MMIO_STALE_DATA))
		pr_info("MMIO Stale Data: %s\n", mmio_strings[mmio_mitigation]);
}

static void __init md_clear_select_mitigation(void)
{
	mds_select_mitigation();
	taa_select_mitigation();
	mmio_select_mitigation();

	/*
	 * As MDS, TAA and MMIO Stale Data mitigations are inter-related, update
	 * and print their mitigation after MDS, TAA and MMIO Stale Data
	 * mitigation selection is done.
	 */
	md_clear_update_mitigation();
}

#undef pr_fmt
#define pr_fmt(fmt)	"SRBDS: " fmt

enum srbds_mitigations {
	SRBDS_MITIGATION_OFF,
	SRBDS_MITIGATION_UCODE_NEEDED,
	SRBDS_MITIGATION_FULL,
	SRBDS_MITIGATION_TSX_OFF,
	SRBDS_MITIGATION_HYPERVISOR,
};

static enum srbds_mitigations srbds_mitigation __read_mostly = SRBDS_MITIGATION_FULL;

static const char * const srbds_strings[] = {
	[SRBDS_MITIGATION_OFF]		= "Vulnerable",
	[SRBDS_MITIGATION_UCODE_NEEDED]	= "Vulnerable: No microcode",
	[SRBDS_MITIGATION_FULL]		= "Mitigation: Microcode",
	[SRBDS_MITIGATION_TSX_OFF]	= "Mitigation: TSX disabled",
	[SRBDS_MITIGATION_HYPERVISOR]	= "Unknown: Dependent on hypervisor status",
};

static bool srbds_off;

void update_srbds_msr(void)
{
	u64 mcu_ctrl;

	if (!boot_cpu_has_bug(X86_BUG_SRBDS))
		return;

	if (boot_cpu_has(X86_FEATURE_HYPERVISOR))
		return;

	if (srbds_mitigation == SRBDS_MITIGATION_UCODE_NEEDED)
		return;

	rdmsrl(MSR_IA32_MCU_OPT_CTRL, mcu_ctrl);

	switch (srbds_mitigation) {
	case SRBDS_MITIGATION_OFF:
	case SRBDS_MITIGATION_TSX_OFF:
		mcu_ctrl |= RNGDS_MITG_DIS;
		break;
	case SRBDS_MITIGATION_FULL:
		mcu_ctrl &= ~RNGDS_MITG_DIS;
		break;
	default:
		break;
	}

	wrmsrl(MSR_IA32_MCU_OPT_CTRL, mcu_ctrl);
}

static void __init srbds_select_mitigation(void)
{
	u64 ia32_cap;

	if (!boot_cpu_has_bug(X86_BUG_SRBDS))
		return;

	/*
	 * Check to see if this is one of the MDS_NO systems supporting TSX that
	 * are only exposed to SRBDS when TSX is enabled or when CPU is affected
	 * by Processor MMIO Stale Data vulnerability.
	 */
	ia32_cap = x86_read_arch_cap_msr();
	if ((ia32_cap & ARCH_CAP_MDS_NO) && !boot_cpu_has(X86_FEATURE_RTM) &&
	    !boot_cpu_has_bug(X86_BUG_MMIO_STALE_DATA))
		srbds_mitigation = SRBDS_MITIGATION_TSX_OFF;
	else if (boot_cpu_has(X86_FEATURE_HYPERVISOR))
		srbds_mitigation = SRBDS_MITIGATION_HYPERVISOR;
	else if (!boot_cpu_has(X86_FEATURE_SRBDS_CTRL))
		srbds_mitigation = SRBDS_MITIGATION_UCODE_NEEDED;
	else if (cpu_mitigations_off() || srbds_off)
		srbds_mitigation = SRBDS_MITIGATION_OFF;

	update_srbds_msr();
	pr_info("%s\n", srbds_strings[srbds_mitigation]);
}

static int __init srbds_parse_cmdline(char *str)
{
	if (!str)
		return -EINVAL;

	if (!boot_cpu_has_bug(X86_BUG_SRBDS))
		return 0;

	srbds_off = !strcmp(str, "off");
	return 0;
}
early_param("srbds", srbds_parse_cmdline);

#undef pr_fmt
#define pr_fmt(fmt)     "Spectre V1 : " fmt

enum spectre_v1_mitigation {
	SPECTRE_V1_MITIGATION_NONE,
	SPECTRE_V1_MITIGATION_AUTO,
};

static enum spectre_v1_mitigation spectre_v1_mitigation __read_mostly =
	SPECTRE_V1_MITIGATION_AUTO;

static const char * const spectre_v1_strings[] = {
	[SPECTRE_V1_MITIGATION_NONE] = "Vulnerable: Load fences, __user pointer sanitization and usercopy barriers only; no swapgs barriers",
	[SPECTRE_V1_MITIGATION_AUTO] = "Mitigation: Load fences, usercopy/swapgs barriers and __user pointer sanitization",
};

/*
 * Does SMAP provide full mitigation against speculative kernel access to
 * userspace?
 */
static bool smap_works_speculatively(void)
{
	if (!boot_cpu_has(X86_FEATURE_SMAP))
		return false;

	/*
	 * On CPUs which are vulnerable to Meltdown, SMAP does not
	 * prevent speculative access to user data in the L1 cache.
	 * Consider SMAP to be non-functional as a mitigation on these
	 * CPUs.
	 */
	if (boot_cpu_has(X86_BUG_CPU_MELTDOWN))
		return false;

	return true;
}

static void __init spectre_v1_select_mitigation(void)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V1) || cpu_mitigations_off()) {
		spectre_v1_mitigation = SPECTRE_V1_MITIGATION_NONE;
		return;
	}

	if (spectre_v1_mitigation == SPECTRE_V1_MITIGATION_AUTO) {
		/*
		 * With Spectre v1, a user can speculatively control either
		 * path of a conditional swapgs with a user-controlled GS
		 * value.  The mitigation is to add lfences to both code paths.
		 *
		 * If FSGSBASE is enabled, the user can put a kernel address in
		 * GS, in which case SMAP provides no protection.
		 *
		 * [ NOTE: Don't check for X86_FEATURE_FSGSBASE until the
		 *	   FSGSBASE enablement patches have been merged. ]
		 *
		 * If FSGSBASE is disabled, the user can only put a user space
		 * address in GS.  That makes an attack harder, but still
		 * possible if there's no SMAP protection.
		 */
		if (!smap_works_speculatively()) {
			/*
			 * Mitigation can be provided from SWAPGS itself if
			 * it is serializing. If not, mitigate with an LFENCE
			 * to stop speculation through swapgs.
			 */
			if (boot_cpu_has_bug(X86_BUG_SWAPGS))
				setup_force_cpu_cap(X86_FEATURE_FENCE_SWAPGS_USER);

			/*
			 * Enable lfences in the kernel entry (non-swapgs)
			 * paths, to prevent user entry from speculatively
			 * skipping swapgs.
			 */
			setup_force_cpu_cap(X86_FEATURE_FENCE_SWAPGS_KERNEL);
		}
	}

	pr_info("%s\n", spectre_v1_strings[spectre_v1_mitigation]);
}

static int __init nospectre_v1_cmdline(char *str)
{
	spectre_v1_mitigation = SPECTRE_V1_MITIGATION_NONE;
	return 0;
}
early_param("nospectre_v1", nospectre_v1_cmdline);

enum spectre_v2_mitigation spectre_v2_enabled = SPECTRE_V2_NONE;

#undef pr_fmt
#define pr_fmt(fmt)     "RETBleed: " fmt

enum retbleed_mitigation {
	RETBLEED_MITIGATION_NONE,
	RETBLEED_MITIGATION_UNRET,
	RETBLEED_MITIGATION_IBPB,
	RETBLEED_MITIGATION_IBRS,
	RETBLEED_MITIGATION_EIBRS,
};

enum retbleed_mitigation_cmd {
	RETBLEED_CMD_OFF,
	RETBLEED_CMD_AUTO,
	RETBLEED_CMD_UNRET,
	RETBLEED_CMD_IBPB,
};

const char * const retbleed_strings[] = {
	[RETBLEED_MITIGATION_NONE]	= "Vulnerable",
	[RETBLEED_MITIGATION_UNRET]	= "Mitigation: untrained return thunk",
	[RETBLEED_MITIGATION_IBPB]	= "Mitigation: IBPB",
	[RETBLEED_MITIGATION_IBRS]	= "Mitigation: IBRS",
	[RETBLEED_MITIGATION_EIBRS]	= "Mitigation: Enhanced IBRS",
};

static enum retbleed_mitigation retbleed_mitigation __read_mostly =
	RETBLEED_MITIGATION_NONE;
static enum retbleed_mitigation_cmd retbleed_cmd __read_mostly =
	RETBLEED_CMD_AUTO;

static int __read_mostly retbleed_nosmt = false;

static int __init retbleed_parse_cmdline(char *str)
{
	while (str) {
		char *next = strchr(str, ',');
		if (next) {
			*next = 0;
			next++;
		}

		if (!strcmp(str, "off")) {
			retbleed_cmd = RETBLEED_CMD_OFF;
		} else if (!strcmp(str, "auto")) {
			retbleed_cmd = RETBLEED_CMD_AUTO;
		} else if (!strcmp(str, "unret")) {
			retbleed_cmd = RETBLEED_CMD_UNRET;
		} else if (!strcmp(str, "ibpb")) {
			retbleed_cmd = RETBLEED_CMD_IBPB;
		} else if (!strcmp(str, "nosmt")) {
			retbleed_nosmt = true;
		} else {
			pr_err("Ignoring unknown retbleed option (%s).", str);
		}

		str = next;
	}

	return 0;
}
early_param("retbleed", retbleed_parse_cmdline);

#define RETBLEED_UNTRAIN_MSG "WARNING: BTB untrained return thunk mitigation is only effective on AMD!\n"
#define RETBLEED_COMPILER_MSG "WARNING: kernel not compiled with RETPOLINE or -mfunction-return capable compiler; falling back to IBPB!\n"
#define RETBLEED_INTEL_MSG "WARNING: Spectre v2 mitigation leaves CPU vulnerable to RETBleed attacks, data leaks possible!\n"

static void __init retbleed_select_mitigation(void)
{
	bool mitigate_smt = false;

	if (!boot_cpu_has_bug(X86_BUG_RETBLEED) || cpu_mitigations_off())
		return;

	switch (retbleed_cmd) {
	case RETBLEED_CMD_OFF:
		return;

	case RETBLEED_CMD_UNRET:
		retbleed_mitigation = RETBLEED_MITIGATION_UNRET;
		break;

	case RETBLEED_CMD_IBPB:
		if (boot_cpu_has(X86_FEATURE_IBPB)) {
			retbleed_mitigation = RETBLEED_MITIGATION_IBPB;
			break;
		} else {
			pr_err("WARNING: CPU does not support IBPB.\n");
		}
		/* fallthrough */
	case RETBLEED_CMD_AUTO:
	default:
		if (boot_cpu_data.x86_vendor == X86_VENDOR_AMD) {
			if (!IS_ENABLED(CONFIG_RETPOLINE) && boot_cpu_has(X86_FEATURE_IBPB)) {
				pr_err(RETBLEED_COMPILER_MSG);
				retbleed_mitigation = RETBLEED_MITIGATION_IBPB;
			} else {
				retbleed_mitigation = RETBLEED_MITIGATION_UNRET;
			}
		}

		/*
		 * The Intel mitigation (IBRS or eIBRS) was already selected in
		 * spectre_v2_select_mitigation().  'retbleed_mitigation' will
		 * be set accordingly below.
		 */

		break;
	}

	switch (retbleed_mitigation) {
	case RETBLEED_MITIGATION_UNRET:
		setup_force_cpu_cap(X86_FEATURE_RETHUNK);
		setup_force_cpu_cap(X86_FEATURE_UNRET);

		if (boot_cpu_data.x86_vendor != X86_VENDOR_AMD)
			pr_err(RETBLEED_UNTRAIN_MSG);

		mitigate_smt = true;
		break;

	case RETBLEED_MITIGATION_IBPB:
		setup_force_cpu_cap(X86_FEATURE_ENTRY_IBPB);
		mitigate_smt = true;
		break;

	default:
		break;
	}

	if (mitigate_smt && (!boot_cpu_has(X86_FEATURE_STIBP) ||
	     !(x86_spec_ctrl_base & SPEC_CTRL_STIBP)) &&
	    (retbleed_nosmt || cpu_mitigations_auto_nosmt()))
		cpu_smt_disable(false);

	/*
	 * Let IBRS trump all on Intel without affecting the effects of the
	 * retbleed= cmdline option.
	 */
	if (boot_cpu_data.x86_vendor == X86_VENDOR_INTEL) {
		switch (spectre_v2_enabled) {
		case SPECTRE_V2_IBRS_ALWAYS:
		case SPECTRE_V2_IBRS:
			retbleed_mitigation = RETBLEED_MITIGATION_IBRS;
			break;
		case SPECTRE_V2_IBRS_ENHANCED:
			retbleed_mitigation = RETBLEED_MITIGATION_EIBRS;
			break;
		default:
			pr_err(RETBLEED_INTEL_MSG);
		}
	}

	pr_info("%s\n", retbleed_strings[retbleed_mitigation]);
}

#undef pr_fmt
#define pr_fmt(fmt)     "Spectre V2 : " fmt

#define SPECTRE_V2_LFENCE_MSG "WARNING: AMD retpoline (LFENCE/JMP) is not a recommended mitigation for this CPU, data leaks possible!\n"

static inline bool match_option(const char *arg, int arglen, const char *opt)
{
	int len = strlen(opt);

	return len == arglen && !strncmp(arg, opt, len);
}

static const struct {
	const char *option;
	enum spectre_v2_mitigation_cmd cmd;
	bool secure;
} mitigation_options[] = {
	{ "off",		SPECTRE_V2_CMD_NONE,		   false },
	{ "on",			SPECTRE_V2_CMD_FORCE,		   true },
	{ "retpoline",		SPECTRE_V2_CMD_RETPOLINE,	   false },
	{ "retpoline,amd",	SPECTRE_V2_CMD_RETPOLINE_AMD,	   false },
	{ "retpoline,force",	SPECTRE_V2_CMD_RETPOLINE_FORCE,	   false },
	{ "retpoline,ibrs_user",SPECTRE_V2_CMD_RETPOLINE_IBRS_USER,false },
	{ "ibrs",		SPECTRE_V2_CMD_IBRS,		   false },
	{ "ibrs_always",	SPECTRE_V2_CMD_IBRS_ALWAYS,	   false },
	{ "auto",		SPECTRE_V2_CMD_AUTO,		   false },
};

static void __init spec2_print_if_insecure(const char *reason)
{
	if (boot_cpu_has_bug(X86_BUG_SPECTRE_V2))
		pr_info("%s selected on command line.\n", reason);
}

static void __init spec2_print_if_secure(const char *reason)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V2))
		pr_info("%s selected on command line.\n", reason);
}

static enum spectre_v2_mitigation_cmd __init spectre_v2_parse_cmdline(void)
{
	char arg[20];
	int ret, i;
	enum spectre_v2_mitigation_cmd cmd = SPECTRE_V2_CMD_AUTO;

	if (cmdline_find_option_bool(boot_command_line, "nospectre_v2") ||
	    cpu_mitigations_off())
		return SPECTRE_V2_CMD_NONE;
	else {
		ret = cmdline_find_option(boot_command_line, "spectre_v2", arg,
					  sizeof(arg));
		if (ret < 0)
			return SPECTRE_V2_CMD_AUTO;

		for (i = 0; i < ARRAY_SIZE(mitigation_options); i++) {
			if (!match_option(arg, ret, mitigation_options[i].option))
				continue;
			cmd = mitigation_options[i].cmd;
			break;
		}

		if (i >= ARRAY_SIZE(mitigation_options)) {
			pr_err("unknown option (%s). Switching to AUTO select\n",
			       arg);
			return SPECTRE_V2_CMD_AUTO;
		}
	}

	if ((cmd == SPECTRE_V2_CMD_RETPOLINE ||
	     cmd == SPECTRE_V2_CMD_RETPOLINE_AMD ||
	     cmd == SPECTRE_V2_CMD_RETPOLINE_FORCE ||
	     cmd == SPECTRE_V2_CMD_RETPOLINE_IBRS_USER) &&
	    !IS_ENABLED(CONFIG_RETPOLINE)) {
		pr_err("%s selected but not compiled in. Switching to AUTO select\n",
		       mitigation_options[i].option);
		return SPECTRE_V2_CMD_AUTO;
	}

	if (cmd == SPECTRE_V2_CMD_RETPOLINE_AMD) {
		/*
		 * Originally, RHEL7 would unconditionally set the capability
		 * X86_FEATURE_RETPOLINE_AMD in init_amd() to alternatively
		 * patch over its retpoline code with a single LFENCE call
		 * before the indirect jump.
		 *
		 * With that becoming a command line option now, we need to
		 * select SPECTRE_V2_CMD_AUTO in case "retpoline,amd" gets
		 * parsed on non-AMD systems.
		 */
		if (boot_cpu_data.x86_vendor != X86_VENDOR_AMD)
			return SPECTRE_V2_CMD_AUTO;

		if (!boot_cpu_has(X86_FEATURE_LFENCE_RDTSC)) {
			pr_warn("%s selected, but CPU doesn't have a serializing LFENCE. " \
				"Switching to AUTO select\n",
				mitigation_options[i].option);
			return SPECTRE_V2_CMD_AUTO;
		}
	}

	/*
	 * RETBleed affected CPUs (Intel) depend on IBRS as an effective
	 * mitigation mechanism. We'll override spectre_v2=retpoline with
	 * spectre_v2=auto here, unless the old behavior is forced by
	 * amending ',force' to the spectre_v2 cmdline.
	 */
	if (boot_cpu_has_bug(X86_BUG_RETBLEED) &&
	    boot_cpu_data.x86_vendor == X86_VENDOR_INTEL) {
		switch (cmd) {
		case SPECTRE_V2_CMD_RETPOLINE:
			pr_warn("WARNING: %s selected but CPU is affected by RETBleed. " \
				"Switching to AUTO select\n",
				mitigation_options[i].option);
			return SPECTRE_V2_CMD_AUTO;

		case SPECTRE_V2_CMD_RETPOLINE_FORCE:
			pr_warn("WARNING: %s selected but CPU is affected by RETBleed. " \
				"Switching to \"auto\" is advised\n",
				mitigation_options[i].option);
		default:
			break;
		}
	}

	if (mitigation_options[i].secure)
		spec2_print_if_secure(mitigation_options[i].option);
	else
		spec2_print_if_insecure(mitigation_options[i].option);

	return cmd;
}

void __spectre_v2_select_mitigation(void)
{
	const bool full_retpoline = IS_ENABLED(CONFIG_RETPOLINE) && retp_compiler();
	enum spectre_v2_mitigation_cmd cmd = spectre_v2_cmd;

	/* Initialize Indirect Branch Prediction Barrier if supported */
	if (boot_cpu_has(X86_FEATURE_IBPB)) {
		setup_force_cpu_cap(X86_FEATURE_USE_IBPB);
		pr_info("Enabling Indirect Branch Prediction Barrier\n");
	}

	/*
	 * If the CPU is not affected and the command line mode is NONE or AUTO
	 * then nothing to do.
	 */
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V2) &&
	    (cmd == SPECTRE_V2_CMD_NONE || cmd == SPECTRE_V2_CMD_AUTO))
		return;

	switch (cmd) {
	case SPECTRE_V2_CMD_NONE:
		return;

	case SPECTRE_V2_CMD_FORCE:
	case SPECTRE_V2_CMD_AUTO:
		if (boot_cpu_has(X86_FEATURE_IBRS_ENHANCED)) {
			spec_ctrl_enable_ibrs_enhanced();
			return;
		}
		break;

	case SPECTRE_V2_CMD_RETPOLINE_FORCE:
	case SPECTRE_V2_CMD_RETPOLINE:
		spec_ctrl_enable_retpoline();
		return;

	case SPECTRE_V2_CMD_RETPOLINE_AMD:
		pr_warn(SPECTRE_V2_LFENCE_MSG);
		spec_ctrl_enable_retpoline_amd();
		return;

	case SPECTRE_V2_CMD_IBRS:
		if (spec_ctrl_force_enable_ibrs())
			return;
		break;

	case SPECTRE_V2_CMD_IBRS_ALWAYS:
		if (spec_ctrl_enable_ibrs_always() ||
		    spec_ctrl_force_enable_ibp_disabled())
			return;
		break;

	case SPECTRE_V2_CMD_RETPOLINE_IBRS_USER:
		if (spec_ctrl_enable_retpoline_ibrs_user())
			return;
		break;
	}

	if (spec_ctrl_cond_enable_ibrs(full_retpoline))
		return;

	if (spec_ctrl_cond_enable_ibp_disabled())
		return;

	spec_ctrl_enable_retpoline();
}

void spectre_v2_print_mitigation(void)
{

	pr_info("%s\n", spectre_v2_strings[spec_ctrl_get_mitigation()]);
}

#undef pr_fmt
#define pr_fmt(fmt) fmt

/* Update the static key controlling the MDS CPU buffer clear in idle */
static void update_mds_branch_idle(void)
{
	u64 ia32_cap = x86_read_arch_cap_msr();

	/*
	 * Enable the idle clearing if SMT is active on CPUs which are
	 * affected only by MSBDS and not any other MDS variant.
	 *
	 * The other variants cannot be mitigated when SMT is enabled, so
	 * clearing the buffers on idle just to prevent the Store Buffer
	 * repartitioning leak would be a window dressing exercise.
	 */
	if (!boot_cpu_has(X86_BUG_MSBDS_ONLY))
		return;

	if (sched_smt_active()) {
		if (!static_key_enabled(&mds_idle_clear))
			static_key_slow_inc(&mds_idle_clear);
	} else if (mmio_mitigation == MMIO_MITIGATION_OFF ||
		   (ia32_cap & ARCH_CAP_FBSDP_NO)) {
		if (static_key_enabled(&mds_idle_clear))
			static_key_slow_dec(&mds_idle_clear);
	}
}

#define MDS_MSG_SMT "MDS CPU bug present and SMT on, data leak possible. See https://www.kernel.org/doc/html/latest/admin-guide/hw-vuln/mds.html for more details.\n"
#define TAA_MSG_SMT "TAA CPU bug present and SMT on, data leak possible. See https://www.kernel.org/doc/html/latest/admin-guide/hw-vuln/tsx_async_abort.html for more details.\n"
#define MMIO_MSG_SMT "MMIO Stale Data CPU bug present and SMT on, data leak possible. See https://www.kernel.org/doc/html/latest/admin-guide/hw-vuln/processor_mmio_stale_data.html for more details.\n"

void arch_smt_update(void)
{
	mutex_lock(&spec_ctrl_mutex);

	switch (mds_mitigation) {
	case MDS_MITIGATION_FULL:
	case MDS_MITIGATION_VMWERV:
		if (sched_smt_active() && !boot_cpu_has(X86_BUG_MSBDS_ONLY))
			pr_warn_once(MDS_MSG_SMT);
		update_mds_branch_idle();
		break;
	case MDS_MITIGATION_OFF:
		break;
	}

	switch (taa_mitigation) {
	case TAA_MITIGATION_VERW:
	case TAA_MITIGATION_UCODE_NEEDED:
		if (sched_smt_active())
			pr_warn_once(TAA_MSG_SMT);
		break;
	case TAA_MITIGATION_TSX_DISABLED:
	case TAA_MITIGATION_OFF:
		break;
	}

	switch (mmio_mitigation) {
	case MMIO_MITIGATION_VERW:
	case MMIO_MITIGATION_UCODE_NEEDED:
		if (sched_smt_active())
			pr_warn_once(MMIO_MSG_SMT);
		break;
	case MMIO_MITIGATION_OFF:
		break;
	}

	mutex_unlock(&spec_ctrl_mutex);
}

/* Disable in-kernel use of non-RSB RET predictors */
static void __init spec_ctrl_disable_kernel_rrsba(void)
{
	u64 ia32_cap;

	if (!boot_cpu_has(X86_FEATURE_RRSBA_CTRL))
		return;

	ia32_cap = x86_read_arch_cap_msr();

	if (ia32_cap & ARCH_CAP_RRSBA) {
		x86_spec_ctrl_base |= SPEC_CTRL_RRSBA_DIS_S;
		native_wrmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
	}
}

static void __init spectre_v2_select_mitigation(void)
{
	enum spectre_v2_mitigation mode;

	spectre_v2_cmd = spectre_v2_parse_cmdline();
	__spectre_v2_select_mitigation();

	/*
	 * Disable alternate RSB predictions in kernel when indirect CALLs and
	 * JMPs gets protection against BHI and Intramode-BTI, but RET
	 * prediction from a non-RSB predictor is still a risk.
	 */
	barrier();
	mode = spec_ctrl_get_mitigation();
	if (mode == SPECTRE_V2_IBRS_ENHANCED ||
	    mode == SPECTRE_V2_RETPOLINE_IBRS_USER ||
	    mode == SPECTRE_V2_RETPOLINE)
		spec_ctrl_disable_kernel_rrsba();

	spectre_v2_print_mitigation();

	/*
	 * If spectre v2 protection has been enabled, unconditionally fill
	 * RSB during a context switch; this protects against two independent
	 * issues:
	 *
	 *	- RSB underflow (and switch to BTB) on Skylake+
	 *	- SpectreRSB variant of spectre v2 on X86_BUG_SPECTRE_V2 CPUs
	 */
	if (boot_cpu_has_bug(X86_BUG_SPECTRE_V2) && mode != SPECTRE_V2_NONE) {
		setup_force_cpu_cap(X86_FEATURE_RSB_CTXSW);
		pr_info("Filling RSB on context switch\n");
	}
}

#undef pr_fmt

#define pr_fmt(fmt)    "Speculative Store Bypass: " fmt

enum ssb_mitigation ssb_mode = SPEC_STORE_BYPASS_NONE;

/* The kernel command line selection */
enum ssb_mitigation_cmd {
	SPEC_STORE_BYPASS_CMD_NONE,
	SPEC_STORE_BYPASS_CMD_AUTO,
	SPEC_STORE_BYPASS_CMD_ON,
	SPEC_STORE_BYPASS_CMD_PRCTL,
	SPEC_STORE_BYPASS_CMD_SECCOMP,
};

static enum ssb_mitigation_cmd ssb_cmd = SPEC_STORE_BYPASS_CMD_NONE;

static const char *ssb_strings[] = {
	[SPEC_STORE_BYPASS_NONE]	= "Vulnerable",
	[SPEC_STORE_BYPASS_DISABLE]	= "Mitigation: Speculative Store Bypass disabled",
	[SPEC_STORE_BYPASS_PRCTL]	= "Mitigation: Speculative Store Bypass disabled via prctl",
	[SPEC_STORE_BYPASS_SECCOMP]	= "Mitigation: Speculative Store Bypass disabled via prctl and seccomp",
};

static const struct {
	const char *option;
	enum ssb_mitigation_cmd cmd;
} ssb_mitigation_options[] = {
	{ "auto",	SPEC_STORE_BYPASS_CMD_AUTO },   /* Platform decides */
	{ "on",		SPEC_STORE_BYPASS_CMD_ON },     /* Disable Speculative Store Bypass */
	{ "off",	SPEC_STORE_BYPASS_CMD_NONE },   /* Don't touch Speculative Store Bypass */
	{ "prctl",	SPEC_STORE_BYPASS_CMD_PRCTL },  /* Disable Speculative Store Bypass via prctl */
	{ "seccomp",	SPEC_STORE_BYPASS_CMD_SECCOMP}, /* Disable Speculative Store Bypass via prctl and seccomp */
};

static enum ssb_mitigation_cmd __init __ssb_parse_cmdline(void)
{
	enum ssb_mitigation_cmd cmd = SPEC_STORE_BYPASS_CMD_AUTO;
	char arg[20];
	int ret, i;

	if (cmdline_find_option_bool(boot_command_line, "nospec_store_bypass_disable") ||
	    cpu_mitigations_off()) {
		return SPEC_STORE_BYPASS_CMD_NONE;
	} else {
		ret = cmdline_find_option(boot_command_line, "spec_store_bypass_disable",
					  arg, sizeof(arg));
		if (ret < 0)
			return SPEC_STORE_BYPASS_CMD_AUTO;

		for (i = 0; i < ARRAY_SIZE(ssb_mitigation_options); i++) {
			if (!match_option(arg, ret, ssb_mitigation_options[i].option))
				continue;

			cmd = ssb_mitigation_options[i].cmd;
			break;
		}

		if (i >= ARRAY_SIZE(ssb_mitigation_options)) {
			pr_err("unknown option (%s). Switching to AUTO select\n", arg);
			return SPEC_STORE_BYPASS_CMD_AUTO;
		}
	}

	return cmd;
}

/*
 * The SSB command line parsing is now separated from SSB mitigation
 * selection as the boot command line buffer will not be available after
 * init and so could not be used with late microcode update.
 */
static void  __init ssb_parse_cmdline(void)
{
	ssb_cmd = __ssb_parse_cmdline();
}

static enum ssb_mitigation __ssb_select_mitigation(void)
{
	enum ssb_mitigation mode = SPEC_STORE_BYPASS_NONE;
	enum ssb_mitigation_cmd cmd = ssb_cmd;

	if (!boot_cpu_has(X86_FEATURE_SSBD))
		return mode;

	if (!boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS) &&
	    (cmd == SPEC_STORE_BYPASS_CMD_NONE ||
	     cmd == SPEC_STORE_BYPASS_CMD_AUTO))
		return mode;

	switch (cmd) {
	case SPEC_STORE_BYPASS_CMD_AUTO:
	case SPEC_STORE_BYPASS_CMD_SECCOMP:
		/*
		 * Choose prctl+seccomp as the default mode if seccomp is
		 * enabled.
		 */
		if (IS_ENABLED(CONFIG_SECCOMP))
			mode = SPEC_STORE_BYPASS_SECCOMP;
		else
			mode = SPEC_STORE_BYPASS_PRCTL;
		break;
	case SPEC_STORE_BYPASS_CMD_ON:
		mode = SPEC_STORE_BYPASS_DISABLE;
		break;
	case SPEC_STORE_BYPASS_CMD_PRCTL:
		mode = SPEC_STORE_BYPASS_PRCTL;
		break;
	case SPEC_STORE_BYPASS_CMD_NONE:
		break;
	}

	/*
	 * We have three CPU feature flags that are in play here:
	 *  - X86_BUG_SPEC_STORE_BYPASS - CPU is susceptible.
	 *  - X86_FEATURE_SSBD - CPU is able to turn off speculative store bypass
	 *  - X86_FEATURE_SPEC_STORE_BYPASS_DISABLE - engage the mitigation
	 */
	if (mode == SPEC_STORE_BYPASS_DISABLE) {
		setup_force_cpu_cap(X86_FEATURE_SPEC_STORE_BYPASS_DISABLE);
		/*
		 * Intel uses the SPEC CTRL MSR Bit(2) for this, while AMD may
		 * use a completely different MSR and bit dependent on family.
		 */
		/*
		 * Always set the SSBD bit for both AMD & Intel.
		 */
		x86_spec_ctrl_base |= SPEC_CTRL_SSBD;
		if (!static_cpu_has(X86_FEATURE_MSR_SPEC_CTRL))
			x86_amd_ssbd_enable();
		else {
			x86_spec_ctrl_mask |= SPEC_CTRL_SSBD;
			wrmsrl(MSR_IA32_SPEC_CTRL, x86_spec_ctrl_base);
		}
	}

	return mode;
}

void ssb_print_mitigation()
{
	pr_info("%s\n", ssb_strings[ssb_mode]);
}

void ssb_select_mitigation()
{
	ssb_mode = __ssb_select_mitigation();

	/*
	 * Enable ssbd_userset_key if the SSBD is now user settable.
	 */
	if (!static_key_enabled(&ssbd_userset_key) &&
	   (ssb_mode >= SPEC_STORE_BYPASS_PRCTL))
		static_key_slow_inc(&ssbd_userset_key);

	if (boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
		ssb_print_mitigation();
}

#undef pr_fmt
#define pr_fmt(fmt)     "Speculation prctl: " fmt

static void task_update_spec_tif(struct task_struct *tsk)
{
	/* Force the update of the real TIF bits */
	set_tsk_thread_flag(tsk, TIF_SPEC_FORCE_UPDATE);

	/*
	 * Immediately update the speculation control MSRs for the current
	 * task, but for a non-current task delay setting the CPU
	 * mitigation until it is scheduled next.
	 *
	 * This can only happen for SECCOMP mitigation. For PRCTL it's
	 * always the current task.
	 */
	if (tsk == current)
		speculation_ctrl_update_current();
}

static int ssb_prctl_set(struct task_struct *task, unsigned long ctrl)
{
	if (ssb_mode != SPEC_STORE_BYPASS_PRCTL &&
	    ssb_mode != SPEC_STORE_BYPASS_SECCOMP)
		return -ENXIO;

	switch (ctrl) {
	case PR_SPEC_ENABLE:
		/* If speculation is force disabled, enable is not allowed */
		if (task_spec_ssb_force_disable(task))
			return -EPERM;
		task_clear_spec_ssb_disable(task);
		task_clear_spec_ssb_noexec(task);
		task_update_spec_tif(task);
		break;
	case PR_SPEC_DISABLE:
		task_set_spec_ssb_disable(task);
		task_clear_spec_ssb_noexec(task);
		task_update_spec_tif(task);
		break;
	case PR_SPEC_FORCE_DISABLE:
		task_set_spec_ssb_disable(task);
		task_set_spec_ssb_force_disable(task);
		task_clear_spec_ssb_noexec(task);
		task_update_spec_tif(task);
		break;
	case PR_SPEC_DISABLE_NOEXEC:
		if (task_spec_ssb_force_disable(task))
			return -EPERM;
		task_set_spec_ssb_disable(task);
		task_set_spec_ssb_noexec(task);
		task_update_spec_tif(task);
		break;
	default:
		return -ERANGE;
	}
	return 0;
}

int arch_prctl_spec_ctrl_set(struct task_struct *task, unsigned long which,
			     unsigned long ctrl)
{
	switch (which) {
	case PR_SPEC_STORE_BYPASS:
		return ssb_prctl_set(task, ctrl);
	default:
		return -ENODEV;
	}
}

#ifdef CONFIG_SECCOMP
void arch_seccomp_spec_mitigate(struct task_struct *task)
{
	if (ssb_mode == SPEC_STORE_BYPASS_SECCOMP)
		ssb_prctl_set(task, PR_SPEC_FORCE_DISABLE);
}
#endif

static int ssb_prctl_get(struct task_struct *task)
{
	switch (ssb_mode) {
	case SPEC_STORE_BYPASS_DISABLE:
		return PR_SPEC_DISABLE;
	case SPEC_STORE_BYPASS_SECCOMP:
	case SPEC_STORE_BYPASS_PRCTL:
		if (task_spec_ssb_force_disable(task))
			return PR_SPEC_PRCTL | PR_SPEC_FORCE_DISABLE;
		if (task_spec_ssb_noexec(task))
			return PR_SPEC_PRCTL | PR_SPEC_DISABLE_NOEXEC;
		if (task_spec_ssb_disable(task))
			return PR_SPEC_PRCTL | PR_SPEC_DISABLE;
		return PR_SPEC_PRCTL | PR_SPEC_ENABLE;
	default:
		if (boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
			return PR_SPEC_ENABLE;
		return PR_SPEC_NOT_AFFECTED;
	}
}

int arch_prctl_spec_ctrl_get(struct task_struct *task, unsigned long which)
{
	switch (which) {
	case PR_SPEC_STORE_BYPASS:
		return ssb_prctl_get(task);
	default:
		return -ENODEV;
	}
}

int itlb_multihit_kvm_mitigation = -1;
EXPORT_SYMBOL_GPL(itlb_multihit_kvm_mitigation);

#undef pr_fmt
#define pr_fmt(fmt)	"L1TF: " fmt

/* Default mitigation for L1TF-affected CPUs */
enum l1tf_mitigations l1tf_mitigation = L1TF_MITIGATION_FLUSH;
#if IS_ENABLED(CONFIG_KVM_INTEL)
EXPORT_SYMBOL_GPL(l1tf_mitigation);

enum vmx_l1d_flush_state l1tf_vmx_mitigation = VMENTER_L1D_FLUSH_AUTO;
EXPORT_SYMBOL_GPL(l1tf_vmx_mitigation);
#endif

/*
 * These CPUs all support 44bits physical address space internally in the
 * cache but CPUID can report a smaller number of physical address bits.
 *
 * The L1TF mitigation uses the top most address bit for the inversion of
 * non present PTEs. When the installed memory reaches into the top most
 * address bit due to memory holes, which has been observed on machines
 * which report 36bits physical address bits and have 32G RAM installed,
 * then the mitigation range check in l1tf_select_mitigation() triggers.
 * This is a false positive because the mitigation is still possible due to
 * the fact that the cache uses 44bit internally. Use the cache bits
 * instead of the reported physical bits and adjust them on the affected
 * machines to 44bit if the reported bits are less than 44.
 */
static void override_cache_bits(struct cpuinfo_x86 *c)
{
	if (c->x86 != 6)
		return;

	switch (c->x86_model) {
	case INTEL_FAM6_NEHALEM:
	case INTEL_FAM6_WESTMERE:
	case INTEL_FAM6_SANDYBRIDGE:
	case INTEL_FAM6_IVYBRIDGE:
	case INTEL_FAM6_HASWELL_CORE:
	case INTEL_FAM6_HASWELL_ULT:
	case INTEL_FAM6_HASWELL_GT3E:
	case INTEL_FAM6_BROADWELL_CORE:
	case INTEL_FAM6_BROADWELL_GT3E:
	case INTEL_FAM6_SKYLAKE_MOBILE:
	case INTEL_FAM6_SKYLAKE_DESKTOP:
	case INTEL_FAM6_KABYLAKE_MOBILE:
	case INTEL_FAM6_KABYLAKE_DESKTOP:
		if (c->x86_cache_bits < 44)
			c->x86_cache_bits = 44;
		break;
	}
}

static void __init l1tf_select_mitigation(void)
{
	u64 half_pa;

	if (!boot_cpu_has_bug(X86_BUG_L1TF))
		return;

	override_cache_bits(&boot_cpu_data);

	if (cpu_mitigations_off())
		l1tf_mitigation = L1TF_MITIGATION_OFF;
	else if (cpu_mitigations_auto_nosmt())
		l1tf_mitigation = L1TF_MITIGATION_FLUSH_NOSMT;

	switch (l1tf_mitigation) {
	case L1TF_MITIGATION_OFF:
	case L1TF_MITIGATION_FLUSH_NOWARN:
	case L1TF_MITIGATION_FLUSH:
		break;
	case L1TF_MITIGATION_FLUSH_NOSMT:
	case L1TF_MITIGATION_FULL:
		cpu_smt_disable(false);
		break;
	case L1TF_MITIGATION_FULL_FORCE:
		cpu_smt_disable(true);
		break;
	}

#if PAGETABLE_LEVELS == 2
	pr_warn("Kernel not compiled for PAE. No mitigation for L1TF\n");
	return;
#endif

	half_pa = (u64)l1tf_pfn_limit() << PAGE_SHIFT;
	if (e820_any_mapped(half_pa, ULLONG_MAX - half_pa, E820_RAM)) {
		pr_warn("System has more than MAX_PA/2 memory. L1TF mitigation not effective.\n");
		return;
	}

	setup_force_cpu_cap(X86_FEATURE_L1TF_PTEINV);
}

static int __init l1tf_cmdline(char *str)
{
	if (!boot_cpu_has_bug(X86_BUG_L1TF))
		return 0;

	if (!str)
		return -EINVAL;

	if (!strcmp(str, "off"))
		l1tf_mitigation = L1TF_MITIGATION_OFF;
	else if (!strcmp(str, "flush,nowarn"))
		l1tf_mitigation = L1TF_MITIGATION_FLUSH_NOWARN;
	else if (!strcmp(str, "flush"))
		l1tf_mitigation = L1TF_MITIGATION_FLUSH;
	else if (!strcmp(str, "flush,nosmt"))
		l1tf_mitigation = L1TF_MITIGATION_FLUSH_NOSMT;
	else if (!strcmp(str, "full"))
		l1tf_mitigation = L1TF_MITIGATION_FULL;
	else if (!strcmp(str, "full,force"))
		l1tf_mitigation = L1TF_MITIGATION_FULL_FORCE;

	return 0;
}
early_param("l1tf", l1tf_cmdline);

#undef pr_fmt
#define pr_fmt(fmt) fmt

#ifdef CONFIG_SYSFS

#define L1TF_DEFAULT_MSG "Mitigation: PTE Inversion"

#if IS_ENABLED(CONFIG_KVM_INTEL)
static const char *l1tf_vmx_states[] = {
	[VMENTER_L1D_FLUSH_AUTO]		= "auto",
	[VMENTER_L1D_FLUSH_NEVER]		= "vulnerable",
	[VMENTER_L1D_FLUSH_COND]		= "conditional cache flushes",
	[VMENTER_L1D_FLUSH_ALWAYS]		= "cache flushes",
	[VMENTER_L1D_FLUSH_EPT_DISABLED]	= "EPT disabled",
	[VMENTER_L1D_FLUSH_NOT_REQUIRED]	= "flush not necessary"
};

static ssize_t l1tf_show_state(char *buf)
{
	if (l1tf_vmx_mitigation == VMENTER_L1D_FLUSH_AUTO)
		return sprintf(buf, "%s\n", L1TF_DEFAULT_MSG);

	if (l1tf_vmx_mitigation == VMENTER_L1D_FLUSH_EPT_DISABLED ||
	    (l1tf_vmx_mitigation == VMENTER_L1D_FLUSH_NEVER &&
	     sched_smt_active())) {
		return sprintf(buf, "%s; VMX: %s\n", L1TF_DEFAULT_MSG,
			       l1tf_vmx_states[l1tf_vmx_mitigation]);
	}

	return sprintf(buf, "%s; VMX: %s, SMT %s\n", L1TF_DEFAULT_MSG,
		       l1tf_vmx_states[l1tf_vmx_mitigation],
		       sched_smt_active() ? "vulnerable" : "disabled");
}

static ssize_t itlb_multihit_show_state(char *buf)
{
	if (itlb_multihit_kvm_mitigation == -1)
		return sprintf(buf, "Processor vulnerable\n");

	if (itlb_multihit_kvm_mitigation)
		return sprintf(buf, "KVM: Mitigation: Split huge pages\n");
	else
		return sprintf(buf, "KVM: Vulnerable\n");
}
#else
static ssize_t l1tf_show_state(char *buf)
{
	return sprintf(buf, "%s\n", L1TF_DEFAULT_MSG);
}

static ssize_t itlb_multihit_show_state(char *buf)
{
	return sprintf(buf, "Processor vulnerable\n");
}
#endif

static ssize_t mds_show_state(char *buf)
{
	if (x86_hyper) {
		return sprintf(buf, "%s; SMT Host state unknown\n",
			       mds_strings[mds_mitigation]);
	}

	if (boot_cpu_has(X86_BUG_MSBDS_ONLY)) {
		return sprintf(buf, "%s; SMT %s\n", mds_strings[mds_mitigation],
			       (mds_mitigation == MDS_MITIGATION_OFF ? "vulnerable" :
			        sched_smt_active() ? "mitigated" : "disabled"));
	}

	return sprintf(buf, "%s; SMT %s\n", mds_strings[mds_mitigation],
		       sched_smt_active() ? "vulnerable" : "disabled");
}

static ssize_t tsx_async_abort_show_state(char *buf)
{
	if ((taa_mitigation == TAA_MITIGATION_TSX_DISABLED) ||
	    (taa_mitigation == TAA_MITIGATION_OFF))
		return sprintf(buf, "%s\n", taa_strings[taa_mitigation]);

	if (boot_cpu_has(X86_FEATURE_HYPERVISOR)) {
		return sprintf(buf, "%s; SMT Host state unknown\n",
			       taa_strings[taa_mitigation]);
	}

	return sprintf(buf, "%s; SMT %s\n", taa_strings[taa_mitigation],
		       sched_smt_active() ? "vulnerable" : "disabled");
}

static ssize_t mmio_stale_data_show_state(char *buf)
{
	if (mmio_mitigation == MMIO_MITIGATION_OFF)
		return sprintf(buf, "%s\n", mmio_strings[mmio_mitigation]);

	if (boot_cpu_has(X86_FEATURE_HYPERVISOR)) {
		return sprintf(buf, "%s; SMT Host state unknown\n",
			       mmio_strings[mmio_mitigation]);
	}

	return sprintf(buf, "%s; SMT %s\n", mmio_strings[mmio_mitigation],
		       sched_smt_active() ? "vulnerable" : "disabled");
}

static char *stibp_state(void)
{
	if (spectre_v2_enabled == SPECTRE_V2_IBRS_ENHANCED)
		return "";

	if (x86_spec_ctrl_base & SPEC_CTRL_STIBP)
		return ", STIBP";
	else
		return "";
}

static char *ibpb_state(void)
{
	if (ibpb_enabled())
		return ", IBPB";
	else
		return "";
}

static ssize_t srbds_show_state(char *buf)
{
	return sprintf(buf, "%s\n", srbds_strings[srbds_mitigation]);
}

static ssize_t retbleed_show_state(char *buf)
{
	if (retbleed_mitigation == RETBLEED_MITIGATION_UNRET) {
	    if (boot_cpu_data.x86_vendor != X86_VENDOR_AMD)
		    return sprintf(buf, "Vulnerable: untrained return thunk on non-Zen uarch\n");

	    return sprintf(buf, "%s; SMT %s\n",
			   retbleed_strings[retbleed_mitigation],
			   !sched_smt_active() ? "disabled" :
			   (x86_spec_ctrl_base & SPEC_CTRL_STIBP) ?
			   "enabled with STIBP protection" : "vulnerable");
	}

	return sprintf(buf, "%s\n", retbleed_strings[retbleed_mitigation]);
}

static ssize_t cpu_show_common(struct device *dev, struct device_attribute *attr,
			char *buf, unsigned int bug)
{
	if (!boot_cpu_has_bug(bug))
		return sprintf(buf, "Not affected\n");

	switch (bug) {
	case X86_BUG_CPU_MELTDOWN:
		if (kaiser_enabled)
			return sprintf(buf, "Mitigation: PTI\n");

		break;

	case X86_BUG_SPECTRE_V1:
		return sprintf(buf, "%s\n", spectre_v1_strings[spectre_v1_mitigation]);

	case X86_BUG_SPECTRE_V2:
		return sprintf(buf, "%s%s%s\n",
			       spectre_v2_strings[spectre_v2_enabled],
			       ibpb_state(),
			       stibp_state());

	case X86_BUG_SPEC_STORE_BYPASS:
		return sprintf(buf, "%s\n", ssb_strings[ssb_mode]);

	case X86_BUG_L1TF:
		if (boot_cpu_has(X86_FEATURE_L1TF_PTEINV))
			return l1tf_show_state(buf);
		break;

	case X86_BUG_MDS:
		return mds_show_state(buf);

	case X86_BUG_TAA:
		return tsx_async_abort_show_state(buf);

	case X86_BUG_ITLB_MULTIHIT:
		return itlb_multihit_show_state(buf);

	case X86_BUG_SRBDS:
		return srbds_show_state(buf);

	case X86_BUG_MMIO_STALE_DATA:
		return mmio_stale_data_show_state(buf);

	case X86_BUG_RETBLEED:
		return retbleed_show_state(buf);

	default:
		break;
	}

	return sprintf(buf, "Vulnerable\n");
}

ssize_t cpu_show_meltdown(struct device *dev,
			  struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_CPU_MELTDOWN);
}

ssize_t cpu_show_spectre_v1(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_SPECTRE_V1);
}

ssize_t cpu_show_spectre_v2(struct device *dev,
			    struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_SPECTRE_V2);
}

ssize_t cpu_show_spec_store_bypass(struct device *dev,
				   struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_SPEC_STORE_BYPASS);
}

ssize_t cpu_show_l1tf(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_L1TF);
}

ssize_t cpu_show_mds(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_MDS);
}

ssize_t cpu_show_tsx_async_abort(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_TAA);
}

ssize_t cpu_show_itlb_multihit(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_ITLB_MULTIHIT);
}

ssize_t cpu_show_srbds(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_SRBDS);
}

ssize_t cpu_show_mmio_stale_data(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_MMIO_STALE_DATA);
}

ssize_t cpu_show_retbleed(struct device *dev, struct device_attribute *attr, char *buf)
{
	return cpu_show_common(dev, attr, buf, X86_BUG_RETBLEED);
}
#endif
