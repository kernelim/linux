/*
 *  Copyright (C) 1994  Linus Torvalds
 *
 *  Cyrix stuff, June 1998 by:
 *	- Rafael R. Reilova (moved everything from head.S),
 *        <rreilova@ececs.uc.edu>
 *	- Channing Corn (tests & fixes),
 *	- Andrew D. Balsa (code cleanup).
 */
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/utsname.h>
#include <linux/cpu.h>
#include <linux/module.h>
#include <asm/bugs.h>
#include <asm/processor.h>
#include <asm/processor-flags.h>
#include <asm/i387.h>
#include <asm/msr.h>
#include <asm/mtrr.h>
#include <asm/vmx.h>
#include <asm/paravirt.h>
#include <asm/alternative.h>
#include <asm/cacheflush.h>
#include <asm/nospec-branch.h>
#include <asm/spec_ctrl.h>
#include <asm/hypervisor.h>
#include <linux/prctl.h>
#include <asm/e820.h>

static void __init l1tf_select_mitigation(void);
static void __init mds_select_mitigation(void);

static inline bool retp_compiler(void)
{
	return IS_ENABLED(RETPOLINE);
}

#ifdef CONFIG_X86_32
static int __init no_halt(char *s)
{
	boot_cpu_data.hlt_works_ok = 0;
	return 1;
}

__setup("no-hlt", no_halt);

static int __init no_387(char *s)
{
	boot_cpu_data.hard_math = 0;
	write_cr0(X86_CR0_TS | X86_CR0_EM | X86_CR0_MP | read_cr0());
	return 1;
}

__setup("no387", no_387);

static double __initdata x = 4195835.0;
static double __initdata y = 3145727.0;

/*
 * This used to check for exceptions..
 * However, it turns out that to support that,
 * the XMM trap handlers basically had to
 * be buggy. So let's have a correct XMM trap
 * handler, and forget about printing out
 * some status at boot.
 *
 * We should really only care about bugs here
 * anyway. Not features.
 */
static void __init check_fpu(void)
{
	s32 fdiv_bug;

	if (!boot_cpu_data.hard_math) {
#ifndef CONFIG_MATH_EMULATION
		printk(KERN_EMERG "No coprocessor found and no math emulation present.\n");
		printk(KERN_EMERG "Giving up.\n");
		for (;;) ;
#endif
		return;
	}

	/*
	 * trap_init() enabled FXSR and company _before_ testing for FP
	 * problems here.
	 *
	 * Test for the divl bug..
	 */
	__asm__("fninit\n\t"
		"fldl %1\n\t"
		"fdivl %2\n\t"
		"fmull %2\n\t"
		"fldl %1\n\t"
		"fsubp %%st,%%st(1)\n\t"
		"fistpl %0\n\t"
		"fwait\n\t"
		"fninit"
		: "=m" (*&fdiv_bug)
		: "m" (*&x), "m" (*&y));

	boot_cpu_data.fdiv_bug = fdiv_bug;
	if (boot_cpu_data.fdiv_bug)
		printk(KERN_WARNING "Hmm, FPU with FDIV bug.\n");
}

static void __init check_hlt(void)
{
	if (boot_cpu_data.x86 >= 5 || paravirt_enabled())
		return;

	printk(KERN_INFO "Checking 'hlt' instruction... ");
	if (!boot_cpu_data.hlt_works_ok) {
		printk("disabled\n");
		return;
	}
	halt();
	halt();
	halt();
	halt();
	printk(KERN_CONT "OK.\n");
}

/*
 *	Most 386 processors have a bug where a POPAD can lock the
 *	machine even from user space.
 */

static void __init check_popad(void)
{
#ifndef CONFIG_X86_POPAD_OK
	int res, inp = (int) &res;

	printk(KERN_INFO "Checking for popad bug... ");
	__asm__ __volatile__(
	  "movl $12345678,%%eax; movl $0,%%edi; pusha; popa; movl (%%edx,%%edi),%%ecx "
	  : "=&a" (res)
	  : "d" (inp)
	  : "ecx", "edi");
	/*
	 * If this fails, it means that any user program may lock the
	 * CPU hard. Too bad.
	 */
	if (res != 12345678)
		printk(KERN_CONT "Buggy.\n");
	else
		printk(KERN_CONT "OK.\n");
#endif
}

/*
 * Check whether we are able to run this kernel safely on SMP.
 *
 * - In order to run on a i386, we need to be compiled for i386
 *   (for due to lack of "invlpg" and working WP on a i386)
 * - In order to run on anything without a TSC, we need to be
 *   compiled for a i486.
 */

static void __init check_config(void)
{
/*
 * We'd better not be a i386 if we're configured to use some
 * i486+ only features! (WP works in supervisor mode and the
 * new "invlpg" and "bswap" instructions)
 */
#if defined(CONFIG_X86_WP_WORKS_OK) || defined(CONFIG_X86_INVLPG) || \
	defined(CONFIG_X86_BSWAP)
	if (boot_cpu_data.x86 == 3)
		panic("Kernel requires i486+ for 'invlpg' and other features");
#endif
}
#endif /* CONFIG_X86_32 */

/*
 * CPU bug word
 */
unsigned long __cpu_bugs __read_mostly;
EXPORT_SYMBOL_GPL(__cpu_bugs);

/* Control MDS CPU buffer clear before idling (halt, mwait) */
bool mds_idle_clear __read_mostly;
EXPORT_SYMBOL_GPL(mds_idle_clear);

static void __init spectre_v1_select_mitigation(void);
static void __init spectre_v2_select_mitigation(void);

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
		printk(KERN_INFO "CPU: ");
		print_cpu_info(&boot_cpu_data);
	}

	/*
	 * Select proper mitigation for any exposure to the Speculative Store
	 * Bypass vulnerability (exposed as a bug in "Memory Disambiguation")
	 * This has to be done before spec_ctrl_init() to make sure that its
	 * SPEC_CTRL MSR value is properly set up.
	 */
	ssb_select_mitigation();

	l1tf_select_mitigation();

	mds_select_mitigation();

	/* Select the proper CPU mitigations before patching alternatives */
	spec_ctrl_init();
	spectre_v1_select_mitigation();
	spectre_v2_select_mitigation();
	spec_ctrl_cpu_init();

#ifdef CONFIG_X86_32
	check_config();
	check_hlt();
	check_popad();
	init_utsname()->machine[1] =
		'0' + (boot_cpu_data.x86 > 6 ? 6 : boot_cpu_data.x86);
#endif
	alternative_instructions();

#ifdef CONFIG_X86_32
	/*
	 * kernel_fpu_begin/end() in check_fpu() relies on the patched
	 * alternative instructions.
	 */
	check_fpu();
#endif

#ifdef CONFIG_X86_64
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
	SPECTRE_V2_CMD_AUTO,
	SPECTRE_V2_CMD_FORCE,
	SPECTRE_V2_CMD_RETPOLINE,
	SPECTRE_V2_CMD_RETPOLINE_IBRS_USER,
	SPECTRE_V2_CMD_IBRS,
	SPECTRE_V2_CMD_IBRS_ALWAYS,
};

static const char *spectre_v2_strings[] = {
	[SPECTRE_V2_NONE]			= "Vulnerable",
	[SPECTRE_V2_RETPOLINE_MINIMAL]		= "Vulnerable: Minimal ASM retpoline",
	[SPECTRE_V2_RETPOLINE_MINIMAL_AMD]	= "Vulnerable: Minimal AMD ASM retpoline",
	[SPECTRE_V2_RETPOLINE_NO_IBPB]		= "Vulnerable: Retpoline without IBPB",
	[SPECTRE_V2_RETPOLINE_AMD]		= "Mitigation: Full AMD retpoline",
	[SPECTRE_V2_RETPOLINE_UNSAFE_MODULE]	= "Vulnerable: Retpoline with unsafe module(s)",
	[SPECTRE_V2_RETPOLINE]			= "Mitigation: Full retpoline",
	[SPECTRE_V2_RETPOLINE_IBRS_USER]	= "Mitigation: Full retpoline and IBRS (user space)",
	[SPECTRE_V2_IBRS]			= "Mitigation: IBRS (kernel)",
	[SPECTRE_V2_IBRS_ALWAYS]		= "Mitigation: IBRS (kernel and user space)",
	[SPECTRE_V2_IBP_DISABLED]		= "Mitigation: IBP disabled",
};

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
	if (!boot_cpu_has_bug(X86_BUG_MDS)) {
		mds_mitigation = MDS_MITIGATION_OFF;
		return;
	}

	if (mds_mitigation == MDS_MITIGATION_FULL) {
		if (!boot_cpu_has(X86_FEATURE_MD_CLEAR))
			mds_mitigation = MDS_MITIGATION_VMWERV;

		setup_force_cpu_cap(X86_FEATURE_MDS_USR_CLR);

		if (mds_nosmt && !boot_cpu_has_bug(X86_BUG_MSBDS_ONLY))
			cpu_smt_disable(false);
	}

	pr_info("%s\n", mds_strings[mds_mitigation]);
}

void mds_print_mitigation(void)
{
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

static bool is_swapgs_serializing(void)
{
	/*
	 * Technically, swapgs isn't serializing on AMD (despite it previously
	 * being documented as such in the APM).  But according to AMD, %gs is
	 * updated non-speculatively, and the issuing of %gs-relative memory
	 * operands will be blocked until the %gs update completes, which is
	 * good enough for our purposes.
	 */
	return boot_cpu_data.x86_vendor == X86_VENDOR_AMD;
}

static void __init spectre_v1_select_mitigation(void)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V1)) {
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

		/*
		 * Mitigation can be provided from SWAPGS itself if
		 * it is serializing. If not, mitigate with an LFENCE.
		 */
		if (!is_swapgs_serializing())
			setup_force_cpu_cap(X86_FEATURE_FENCE_SWAPGS_USER);

		/*
		 * Enable lfences in the kernel entry (non-swapgs)
		 * paths, to prevent user entry from speculatively
		 * skipping swapgs.
		 */
		setup_force_cpu_cap(X86_FEATURE_FENCE_SWAPGS_KERNEL);
	}

	pr_info("%s\n", spectre_v1_strings[spectre_v1_mitigation]);
}

static int __init nospectre_v1_cmdline(char *str)
{
	spectre_v1_mitigation = SPECTRE_V1_MITIGATION_NONE;
	return 0;
}
early_param("nospectre_v1", nospectre_v1_cmdline);

#undef pr_fmt
#define pr_fmt(fmt)     "Spectre V2 : " fmt

static enum spectre_v2_mitigation spectre_v2_enabled = SPECTRE_V2_NONE;
static enum spectre_v2_mitigation spectre_v2_retpoline __read_mostly
		= SPECTRE_V2_NONE;
static enum spectre_v2_mitigation_cmd spectre_v2_cmd __read_mostly
		= SPECTRE_V2_CMD_AUTO;

static void __init spec2_print_if_insecure(const char *reason)
{
	if (boot_cpu_has_bug(X86_BUG_SPECTRE_V2))
		pr_info("%s\n", reason);
}

static void __init spec2_print_if_secure(const char *reason)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V2))
		pr_info("%s\n", reason);
}

static inline bool match_option(const char *arg, int arglen, const char *opt)
{
	int len = strlen(opt);

	return len == arglen && !strncmp(arg, opt, len);
}

static int __init set_nospectre_v2(char *arg)
{
	spectre_v2_cmd = SPECTRE_V2_CMD_NONE;
	return 0;
}
early_param("nospectre_v2", set_nospectre_v2);

static int __init set_spectre_v2(char *arg)
{
	if (!arg)
		return 0;
	if (!strcmp(arg, "off")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_NONE;
	} else if (!strcmp(arg, "on")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_FORCE;
	} else if (!strcmp(arg, "retpoline")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_RETPOLINE;
	} else if (!strcmp(arg, "retpoline,ibrs_user")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_RETPOLINE_IBRS_USER;
	} else if (!strcmp(arg, "ibrs")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_IBRS;
	} else if (!strcmp(arg, "ibrs_always")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_IBRS_ALWAYS;
	} else if (!strcmp(arg, "auto")) {
		spectre_v2_cmd = SPECTRE_V2_CMD_AUTO;
	}
	return 0;
}
early_param("spectre_v2", set_spectre_v2);

void spectre_v2_report_unsafe_module(struct module *mod)
{
	if (retp_compiler() && !is_skylake_era())
		pr_warn_once("WARNING: module '%s' built without retpoline-enabled compiler, may affect Spectre v2 mitigation\n",
			     mod->name);

	if (spectre_v2_retpoline == SPECTRE_V2_RETPOLINE ||
	    spectre_v2_retpoline == SPECTRE_V2_RETPOLINE_AMD)
		spectre_v2_retpoline = SPECTRE_V2_RETPOLINE_UNSAFE_MODULE;

	if (spectre_v2_enabled == SPECTRE_V2_RETPOLINE ||
	    spectre_v2_enabled == SPECTRE_V2_RETPOLINE_AMD)
		spectre_v2_enabled = SPECTRE_V2_RETPOLINE_UNSAFE_MODULE;
}

static enum spectre_v2_mitigation_cmd __init spectre_v2_parse_cmdline(void)
{
	switch (spectre_v2_cmd) {
	case SPECTRE_V2_CMD_NONE:
		spec2_print_if_insecure("disabled on command line.");
		break;

	case SPECTRE_V2_CMD_AUTO:
		break;

	case SPECTRE_V2_CMD_IBRS:
		spec2_print_if_insecure("ibrs selected on command line.");
		break;

	case SPECTRE_V2_CMD_IBRS_ALWAYS:
		spec2_print_if_insecure("ibrs_always selected on command line.");
		break;

	case SPECTRE_V2_CMD_FORCE:
		 spec2_print_if_secure("force enabled on command line.");
		 break;

	case SPECTRE_V2_CMD_RETPOLINE:
		spec2_print_if_insecure("retpoline selected on command line.");
		break;

	case SPECTRE_V2_CMD_RETPOLINE_IBRS_USER:
		spec2_print_if_insecure("retpoline (kernel) and ibrs (user) selected on command line.");
		break;
	}
	return spectre_v2_cmd;
}

void __spectre_v2_select_mitigation(void)
{
	enum spectre_v2_mitigation_cmd cmd = spectre_v2_cmd;
	const bool full_retpoline = IS_ENABLED(CONFIG_RETPOLINE) &&
				    retp_compiler();

	spectre_v2_enabled = SPECTRE_V2_NONE;

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
		/* FALLTRHU */
	case SPECTRE_V2_CMD_AUTO:
		goto auto_mode;

	case SPECTRE_V2_CMD_RETPOLINE:
	case SPECTRE_V2_CMD_RETPOLINE_IBRS_USER:
		if (IS_ENABLED(CONFIG_RETPOLINE))
			goto retpoline;
		break;
	case SPECTRE_V2_CMD_IBRS:
		if (spec_ctrl_force_enable_ibrs())
			return;
		break;
	case SPECTRE_V2_CMD_IBRS_ALWAYS:
		if (spec_ctrl_enable_ibrs_always() ||
		    spec_ctrl_force_enable_ibp_disabled())
			return;
		break;
	}

auto_mode:
	if (spec_ctrl_cond_enable_ibrs(full_retpoline))
		return;

	spec_ctrl_cond_enable_ibp_disabled();

retpoline:
	if (spectre_v2_enabled != SPECTRE_V2_NONE ||
	    spectre_v2_retpoline == SPECTRE_V2_RETPOLINE_UNSAFE_MODULE)
		goto retpoline_ibrs_user;

	if (boot_cpu_data.x86_vendor == X86_VENDOR_AMD) {
		if (!boot_cpu_has(X86_FEATURE_LFENCE_RDTSC)) {
			pr_err("LFENCE not serializing. Switching to generic retpoline\n");
			goto retpoline_generic;
		}
		spectre_v2_enabled = retp_compiler()
				   ? SPECTRE_V2_RETPOLINE_AMD
				   : SPECTRE_V2_RETPOLINE_MINIMAL_AMD;
		setup_force_cpu_cap(X86_FEATURE_RETPOLINE_AMD);
		setup_force_cpu_cap(X86_FEATURE_RETPOLINE);
	} else {
retpoline_generic:
		spectre_v2_enabled = retp_compiler()
				   ? SPECTRE_V2_RETPOLINE
				   : SPECTRE_V2_RETPOLINE_MINIMAL;
		setup_force_cpu_cap(X86_FEATURE_RETPOLINE);
	}

	spectre_v2_retpoline = spectre_v2_enabled;

	/*
	 * Enable RETPOLINE_IBRS_USER mode, if necessary.
	 */
retpoline_ibrs_user:
	if (cmd == SPECTRE_V2_CMD_RETPOLINE_IBRS_USER)
		spec_ctrl_enable_retpoline_ibrs_user();
}

enum spectre_v2_mitigation spectre_v2_get_mitigation(void)
{
	return spectre_v2_enabled;
}

void spectre_v2_set_mitigation(enum spectre_v2_mitigation mode)
{
	spectre_v2_enabled = mode;
}

bool spectre_v2_has_full_retpoline(void)
{
	return spectre_v2_retpoline == SPECTRE_V2_RETPOLINE ||
	       spectre_v2_retpoline == SPECTRE_V2_RETPOLINE_AMD;
}

/*
 * Reset to the original retpoline setting when IBRS is dyamically disabled.
 */
void spectre_v2_retpoline_reset(void)
{
	spectre_v2_enabled = spectre_v2_retpoline;
}

void spectre_v2_print_mitigation(void)
{
	pr_info("%s\n", spectre_v2_strings[spectre_v2_enabled]);
}

#undef pr_fmt
#define pr_fmt(fmt) fmt

/* Update the static key controlling the MDS CPU buffer clear in idle */
static void update_mds_branch_idle(void)
{
	/*
	 * Enable the idle clearing if SMT is active on CPUs which are
	 * affected only by MSBDS and not any other MDS variant.
	 *
	 * The other variants cannot be mitigated when SMT is enabled, so
	 * clearing the buffers on idle just to prevent the Store Buffer
	 * repartitioning leak would be a window dressing exercise.
	 */
	if (!boot_cpu_has_bug(X86_BUG_MSBDS_ONLY))
		return;

	if (sched_smt_active())
		mds_idle_clear = true;
	else
		mds_idle_clear = false;
}

#define MDS_MSG_SMT "MDS CPU bug present and SMT on, data leak possible. See https://www.kernel.org/doc/html/latest/admin-guide/hw-vuln/mds.html for more details.\n"

void arch_smt_update(void)
{
	static DEFINE_MUTEX(spec_ctrl_mutex);

	mutex_lock(&spec_ctrl_mutex);

	switch (mds_mitigation) {
	case MDS_MITIGATION_FULL:
	case MDS_MITIGATION_VMWERV:
		if (sched_smt_active() && !mds_nosmt &&
		   !boot_cpu_has_bug(X86_BUG_MSBDS_ONLY))
			pr_warn_once(MDS_MSG_SMT);
		update_mds_branch_idle();
		break;
	case MDS_MITIGATION_OFF:
		break;
	}

	mutex_unlock(&spec_ctrl_mutex);
}

static void __init spectre_v2_select_mitigation(void)
{
	spectre_v2_parse_cmdline();
	__spectre_v2_select_mitigation();
	spectre_v2_print_mitigation();
}

#undef pr_fmt

#define pr_fmt(fmt)    "Speculative Store Bypass: " fmt

enum ssb_mitigation ssb_mode __read_mostly = SPEC_STORE_BYPASS_NONE;
EXPORT_SYMBOL_GPL(ssb_mode);

/* The kernel command line selection */
enum ssb_mitigation_cmd {
	SPEC_STORE_BYPASS_CMD_NONE,
	SPEC_STORE_BYPASS_CMD_AUTO,
	SPEC_STORE_BYPASS_CMD_ON,
	SPEC_STORE_BYPASS_CMD_PRCTL,
	SPEC_STORE_BYPASS_CMD_SECCOMP,
};

static const char *ssb_strings[] = {
	[SPEC_STORE_BYPASS_NONE]	= "Vulnerable",
	[SPEC_STORE_BYPASS_DISABLE]	= "Mitigation: Speculative Store Bypass disabled",
	[SPEC_STORE_BYPASS_PRCTL]	= "Mitigation: Speculative Store Bypass disabled via prctl",
	[SPEC_STORE_BYPASS_SECCOMP]	= "Mitigation: Speculative Store Bypass disabled via prctl and seccomp",
};

static enum ssb_mitigation_cmd  ssb_cmd = SPEC_STORE_BYPASS_CMD_AUTO;

static int __init set_no_ssbd_disable(char *arg)
{
	ssb_cmd = SPEC_STORE_BYPASS_CMD_NONE;
	return 0;
}
early_param("nospec_store_bypass_disable", set_no_ssbd_disable);

static int __init set_ssbd_disable(char *arg)
{
	if (!arg)
		return 0;

	if (!strcmp(arg, "off")) {
		ssb_cmd = SPEC_STORE_BYPASS_CMD_NONE;
	} else if (!strcmp(arg, "on")) {
		ssb_cmd = SPEC_STORE_BYPASS_CMD_ON;
	} else if (!strcmp(arg, "auto")) {
		ssb_cmd = SPEC_STORE_BYPASS_CMD_AUTO;
	} else if (!strcmp(arg, "prctl")) {
		ssb_cmd = SPEC_STORE_BYPASS_CMD_PRCTL;
	} else if (!strcmp(arg, "seccomp")) {
		ssb_cmd = SPEC_STORE_BYPASS_CMD_SECCOMP;
	}
	return 0;
}
early_param("spec_store_bypass_disable", set_ssbd_disable);

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
		if (!boot_cpu_has(X86_FEATURE_MSR_SPEC_CTRL))
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

void ssb_select_mitigation(void)
{
	ssb_mode = __ssb_select_mitigation();

	if (boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
		ssb_print_mitigation();
}

#undef pr_fmt
#define pr_fmt(fmt)     "Speculation prctl: " fmt

static int ssb_prctl_set(struct task_struct *task, unsigned long ctrl)
{
	bool update;

	if (ssb_mode != SPEC_STORE_BYPASS_PRCTL &&
	    ssb_mode != SPEC_STORE_BYPASS_SECCOMP)
		return -ENXIO;

	switch (ctrl) {
	case PR_SPEC_ENABLE:
		/* If speculation is force disabled, enable is not allowed */
		if (task_spec_ssb_force_disable(task))
			return -EPERM;
		task_clear_spec_ssb_disable(task);
		update = test_and_clear_tsk_thread_flag(task, TIF_SSBD);
		break;
	case PR_SPEC_DISABLE:
		task_set_spec_ssb_disable(task);
		update = !test_and_set_tsk_thread_flag(task, TIF_SSBD);
		break;
	case PR_SPEC_FORCE_DISABLE:
		task_set_spec_ssb_disable(task);
		task_set_spec_ssb_force_disable(task);
		update = !test_and_set_tsk_thread_flag(task, TIF_SSBD);
		break;
	default:
		return -ERANGE;
	}

	/*
	 * If being set on non-current task, delay setting the CPU
	 * mitigation until it is next scheduled.
	 */
	if (task == current && update)
		speculative_store_bypass_update_current();

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

#undef pr_fmt
#define pr_fmt(fmt)	"L1TF: " fmt

/* Default mitigation for L1TF-affected CPUs */
enum l1tf_mitigations l1tf_mitigation = L1TF_MITIGATION_FLUSH;
#if IS_ENABLED(CONFIG_KVM_INTEL)
EXPORT_SYMBOL_GPL(l1tf_mitigation);

enum vmx_l1d_flush_state l1tf_vmx_mitigation __read_mostly = VMENTER_L1D_FLUSH_AUTO;
EXPORT_SYMBOL_GPL(l1tf_vmx_mitigation);
#endif

static void __init l1tf_select_mitigation(void)
{
	u64 half_pa;

	if (!boot_cpu_has_bug(X86_BUG_L1TF))
		return;

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

	/*
	 * This is extremely unlikely to happen because almost all
	 * systems have far more MAX_PA/2 than RAM can be fit into
	 * DIMM slots.
	 */
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
ssize_t cpu_show_meltdown(struct sysdev_class *class, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_CPU_MELTDOWN))
		return sprintf(buf, "Not affected\n");
	if (boot_cpu_has(X86_FEATURE_PTI))
		return sprintf(buf, "Mitigation: PTI\n");
	return sprintf(buf, "Vulnerable\n");
}

ssize_t cpu_show_spectre_v1(struct sysdev_class *class, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V1))
		return sprintf(buf, "Not affected\n");
	/*
	 * Load fences have been added in various places within the RHEL6
	 * kernel to mitigate this vulnerability.
	 */
	return sprintf(buf, "%s\n", spectre_v1_strings[spectre_v1_mitigation]);
}

ssize_t cpu_show_spectre_v2(struct sysdev_class *class, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V2))
		return sprintf(buf, "Not affected\n");
	return sprintf(buf, "%s%s\n", spectre_v2_strings[spectre_v2_enabled],
		       ibpb_enabled() ?  ", IBPB" : "");
}

ssize_t cpu_show_spec_store_bypass(struct sysdev_class *class, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
		return sprintf(buf, "Not affected\n");
	return sprintf(buf, "%s\n", ssb_strings[ssb_mode]);
}

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
#else
static ssize_t l1tf_show_state(char *buf)
{
	return sprintf(buf, "%s\n", L1TF_DEFAULT_MSG);
}
#endif

ssize_t cpu_show_l1tf(struct sysdev_class *class, char *buf)
{
	if (!boot_cpu_has(X86_FEATURE_L1TF_PTEINV))
		return sprintf(buf, "Not affected\n");
	return l1tf_show_state(buf);
}

static ssize_t mds_show_state(char *buf)
{
	if (x86_hyper) {
		return sprintf(buf, "%s; SMT Host state unknown\n",
			       mds_strings[mds_mitigation]);
	}

	if (boot_cpu_has_bug(X86_BUG_MSBDS_ONLY)) {
		return sprintf(buf, "%s; SMT %s\n", mds_strings[mds_mitigation],
			       (mds_mitigation == MDS_MITIGATION_OFF ? "vulnerable" :
			        sched_smt_active() ? "mitigated" : "disabled"));
	}

	return sprintf(buf, "%s; SMT %s\n", mds_strings[mds_mitigation],
		       sched_smt_active() ? "vulnerable" : "disabled");
}

ssize_t cpu_show_mds(struct sysdev_class *class, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_MDS))
		return sprintf(buf, "Not affected\n");
	return mds_show_state(buf);
}
#endif
