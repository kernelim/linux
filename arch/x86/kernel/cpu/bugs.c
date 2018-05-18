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
#include <linux/device.h>
#include <linux/module.h>
#include <asm/bugs.h>
#include <asm/processor.h>
#include <asm/processor-flags.h>
#include <asm/i387.h>
#include <asm/msr.h>
#include <asm/mtrr.h>
#include <asm/paravirt.h>
#include <asm/alternative.h>
#include <asm/cacheflush.h>
#include <asm/nospec-branch.h>
#include <asm/spec_ctrl.h>
#include <linux/prctl.h>

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

static void __init spectre_v2_select_mitigation(void);

void __init check_bugs(void)
{
	identify_boot_cpu();
	spec_ctrl_save_msr();

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

	/* Select the proper spectre mitigation before patching alternatives */
	spec_ctrl_init();
	spectre_v2_select_mitigation();

	spec_ctrl_cpu_init();

#ifdef CONFIG_X86_32
	check_config();
	check_fpu();
	check_hlt();
	check_popad();
	init_utsname()->machine[1] =
		'0' + (boot_cpu_data.x86 > 6 ? 6 : boot_cpu_data.x86);
#endif
	alternative_instructions();

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

void x86_amd_rds_enable(void)
{
	u64 msrval = x86_amd_ls_cfg_base | x86_amd_ls_cfg_rds_mask;

	if (boot_cpu_has(X86_FEATURE_AMD_SSBD))
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
	[SPECTRE_V2_RETPOLINE_SKYLAKE]		= "Vulnerable: Retpoline on Skylake+",
	[SPECTRE_V2_RETPOLINE_AMD]		= "Mitigation: Full AMD retpoline",
	[SPECTRE_V2_RETPOLINE_UNSAFE_MODULE]	= "Vulnerable: Retpoline with unsafe module(s)",
	[SPECTRE_V2_RETPOLINE]			= "Mitigation: Full retpoline",
	[SPECTRE_V2_RETPOLINE_IBRS_USER]	= "Mitigation: Full retpoline and IBRS (user space)",
	[SPECTRE_V2_IBRS]			= "Mitigation: IBRS (kernel)",
	[SPECTRE_V2_IBRS_ALWAYS]		= "Mitigation: IBRS (kernel and user space)",
	[SPECTRE_V2_IBP_DISABLED]		= "Mitigation: IBP disabled",
};

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

		if (retp_compiler() && is_skylake_era())
			spectre_v2_enabled = SPECTRE_V2_RETPOLINE_SKYLAKE;
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
	       spectre_v2_retpoline == SPECTRE_V2_RETPOLINE_AMD ||
	       spectre_v2_retpoline == SPECTRE_V2_RETPOLINE_SKYLAKE;
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

static void __init spectre_v2_select_mitigation(void)
{
	spectre_v2_parse_cmdline();
	__spectre_v2_select_mitigation();
	spectre_v2_print_mitigation();
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
};

static const char *ssb_strings[] = {
	[SPEC_STORE_BYPASS_NONE]	= "Vulnerable",
	[SPEC_STORE_BYPASS_DISABLE]	= "Mitigation: Speculative Store Bypass disabled",
	[SPEC_STORE_BYPASS_PRCTL]	= "Mitigation: Speculative Store Bypass disabled via prctl"
};

static enum ssb_mitigation_cmd  ssb_cmd = SPEC_STORE_BYPASS_CMD_AUTO;

static int __init set_no_rds_disable(char *arg)
{
	ssb_cmd = SPEC_STORE_BYPASS_CMD_NONE;
	return 0;
}
early_param("nospec_store_bypass_disable", set_no_rds_disable);

static int __init set_rds_disable(char *arg)
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
	}
	return 0;
}
early_param("spec_store_bypass_disable", set_rds_disable);

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
		/* Choose prctl as the default mode */
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
		 * Intel uses the SPEC CTRL MSR Bit(2) for this, while AMD uses
		 * a completely different MSR and bit dependent on family.
		 */
		switch (boot_cpu_data.x86_vendor) {
		case X86_VENDOR_INTEL:
			x86_spec_ctrl_base |= FEATURE_ENABLE_SSBD;
			break;
		case X86_VENDOR_AMD:
			x86_amd_rds_enable();
			break;
		}
	}

	return mode;
}

void ssb_select_mitigation()
{
	ssb_mode = __ssb_select_mitigation();

	if (boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
		pr_info("%s\n", ssb_strings[ssb_mode]);
}

#undef pr_fmt

static int ssb_prctl_set(unsigned long ctrl)
{
	bool ssbd = !!test_tsk_thread_flag(current, TIF_SSBD);

	if (ssb_mode != SPEC_STORE_BYPASS_PRCTL)
		return -ENXIO;

	if (ctrl == PR_SPEC_ENABLE)
		clear_tsk_thread_flag(current, TIF_SSBD);
	else
		set_tsk_thread_flag(current, TIF_SSBD);

	if (ssbd != !!test_tsk_thread_flag(current, TIF_SSBD))
		speculative_store_bypass_update();

	return 0;
}

static int ssb_prctl_get(void)
{
	switch (ssb_mode) {
	case SPEC_STORE_BYPASS_DISABLE:
		return PR_SPEC_DISABLE;
	case SPEC_STORE_BYPASS_PRCTL:
		if (test_tsk_thread_flag(current, TIF_SSBD))
			return PR_SPEC_PRCTL | PR_SPEC_DISABLE;
		return PR_SPEC_PRCTL | PR_SPEC_ENABLE;
	default:
		if (boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
			return PR_SPEC_ENABLE;
		return PR_SPEC_NOT_AFFECTED;
	}
}

int arch_prctl_spec_ctrl_set(unsigned long which, unsigned long ctrl)
{
	if (ctrl != PR_SPEC_ENABLE && ctrl != PR_SPEC_DISABLE)
		return -ERANGE;

	switch (which) {
	case PR_SPEC_STORE_BYPASS:
		return ssb_prctl_set(ctrl);
	default:
		return -ENODEV;
	}
}

int arch_prctl_spec_ctrl_get(unsigned long which)
{
	switch (which) {
	case PR_SPEC_STORE_BYPASS:
		return ssb_prctl_get();
	default:
		return -ENODEV;
	}
}

#ifdef CONFIG_SYSFS
ssize_t cpu_show_meltdown(struct device *dev,
			  struct device_attribute *attr, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_CPU_MELTDOWN))
		return sprintf(buf, "Not affected\n");
	if (boot_cpu_has(X86_FEATURE_PTI))
		return sprintf(buf, "Mitigation: PTI\n");
	return sprintf(buf, "Vulnerable\n");
}

ssize_t cpu_show_spectre_v1(struct device *dev,
			    struct device_attribute *attr, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V1))
		return sprintf(buf, "Not affected\n");
	/*
	 * Load fences have been added in various places within the RHEL6
	 * kernel to mitigate this vulnerability.
	 */
	return sprintf(buf, "Mitigation: Load fences\n");
}

ssize_t cpu_show_spectre_v2(struct device *dev,
			    struct device_attribute *attr, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_SPECTRE_V2))
		return sprintf(buf, "Not affected\n");
	return sprintf(buf, "%s\n", spectre_v2_strings[spectre_v2_enabled]);
}

ssize_t cpu_show_spec_store_bypass(struct device *dev,
				   struct device_attribute *attr, char *buf)
{
	if (!boot_cpu_has_bug(X86_BUG_SPEC_STORE_BYPASS))
		return sprintf(buf, "Not affected\n");
	return sprintf(buf, "%s\n", ssb_strings[ssb_mode]);
}
#endif
