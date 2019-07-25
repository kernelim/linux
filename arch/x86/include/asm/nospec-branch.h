/* SPDX-License-Identifier: GPL-2.0 */

#ifndef __NOSPEC_BRANCH_H__
#define __NOSPEC_BRANCH_H__

#include <asm/alternative.h>
#include <asm/alternative-asm.h>
#include <asm/cpufeature.h>

/*
 * Fill the CPU return stack buffer.
 *
 * Each entry in the RSB, if used for a speculative 'ret', contains an
 * infinite 'pause; lfence; jmp' loop to capture speculative execution.
 *
 * This is required in various cases for retpoline and IBRS-based
 * mitigations for the Spectre variant 2 vulnerability. Sometimes to
 * eliminate potentially bogus entries from the RSB, and sometimes
 * purely to ensure that it doesn't get empty, which on some CPUs would
 * allow predictions from other (unwanted!) sources to be used.
 *
 * We define a CPP macro such that it can be used from both .S files and
 * inline assembly. It's possible to do a .macro and then include that
 * from C via asm(".include <asm/nospec-branch.h>") but let's not go there.
 */

#define RSB_CLEAR_LOOPS		32	/* To forcibly overwrite all entries */
#define RSB_FILL_LOOPS		16	/* To avoid underflow */

/*
 * Google experimented with loop-unrolling and this turned out to be
 * the optimal version — two calls, each with their own speculation
 * trap should their return address end up getting used, in a loop.
 */
#define __FILL_RETURN_BUFFER(reg, nr, sp)	\
	mov	$(nr/2), reg;			\
771:						\
	call	772f;				\
773:	/* speculation trap */			\
	pause;					\
	lfence;					\
	jmp	773b;				\
772:						\
	call	774f;				\
775:	/* speculation trap */			\
	pause;					\
	lfence;					\
	jmp	775b;				\
774:						\
	dec	reg;				\
	jnz	771b;				\
	add	$(BITS_PER_LONG/8) * nr, sp;

#ifdef __ASSEMBLY__

/*
 * This should be used immediately before a retpoline alternative.  It tells
 * objtool where the retpolines are so that it can make sense of the control
 * flow by just reading the original instruction(s) and ignoring the
 * alternatives.
 *
 * Since there is no objtool in RHEL6, the .discard.nospec object section
 * is not generated.
 */
.macro ANNOTATE_NOSPEC_ALTERNATIVE
#if 0
	.Lannotate_\@:
	.pushsection .discard.nospec
	.long .Lannotate_\@ - .
	.popsection
#endif
.endm

/*
 * These are the bare retpoline primitives for indirect jmp and call.
 * Do not use these directly; they only exist to make the ALTERNATIVE
 * invocation below less ugly.
 */
.macro RETPOLINE_JMP reg:req
	call	.Ldo_rop_\@
.Lspec_trap_\@:
	pause
	lfence
	jmp	.Lspec_trap_\@
.Ldo_rop_\@:
	mov	\reg, (%_ASM_SP)
	ret
.endm

/*
 * This is a wrapper around RETPOLINE_JMP so the called function in reg
 * returns to the instruction after the macro.
 */
.macro RETPOLINE_CALL reg:req
	jmp	.Ldo_call_\@
.Ldo_retpoline_jmp_\@:
	RETPOLINE_JMP \reg
.Ldo_call_\@:
	call	.Ldo_retpoline_jmp_\@
.endm

/*
 * JMP_NOSPEC and CALL_NOSPEC macros can be used instead of a simple
 * indirect jmp/call which may be susceptible to the Spectre variant 2
 * attack.
 */
.macro JMP_NOSPEC reg:req
#ifdef CONFIG_RETPOLINE
	ANNOTATE_NOSPEC_ALTERNATIVE
	ALTERNATIVE_2 __stringify(jmp *\reg),				\
		__stringify(RETPOLINE_JMP \reg), X86_FEATURE_RETPOLINE,	\
		__stringify(lfence; jmp *\reg), X86_FEATURE_RETPOLINE_AMD
#else
	jmp	*\reg
#endif
.endm

.macro CALL_NOSPEC reg:req
#ifdef CONFIG_RETPOLINE
	ANNOTATE_NOSPEC_ALTERNATIVE
	ALTERNATIVE_2 __stringify(call *\reg),				\
		__stringify(RETPOLINE_CALL \reg), X86_FEATURE_RETPOLINE,\
		__stringify(lfence; call *\reg), X86_FEATURE_RETPOLINE_AMD
#else
	call	*\reg
#endif
.endm

 /*
  * A simpler FILL_RETURN_BUFFER macro. Don't make people use the CPP
  * monstrosity above, manually.
  */
.macro FILL_RETURN_BUFFER_CLOBBER reg=%_ASM_AX
	ALTERNATIVE "jmp .Lskip_rsb_\@",				\
		__stringify(__FILL_RETURN_BUFFER(\reg,			\
			    RSB_CLEAR_LOOPS, %_ASM_SP))			\
		X86_FEATURE_SMEP
.Lskip_rsb_\@:
.endm

.macro FILL_RETURN_BUFFER
	push %_ASM_AX
	FILL_RETURN_BUFFER_CLOBBER reg=%_ASM_AX
	pop %_ASM_AX
.endm

/*
 * MDS_USER_CLEAR_CPU_BUFFERS macro is the assembly equivalent of
 * upstream mds_user_clear_cpu_buffers(). Like the C version, the
 * __KERNEL_DS is used for verw. Alternative is used here as
 * static_key isn't available in RHEL6.
 */
.macro MDS_USER_CLEAR_CPU_BUFFERS
	ALTERNATIVE "jmp .Ldone_\@", "", X86_FEATURE_MDS_USR_CLR

	jmp	.Lverw_\@
	.balign 2
.Lds_\@:
	.word	__KERNEL_DS
.Lverw_\@:
	verw	.Lds_\@(%rip)
.Ldone_\@:
.endm

#else /* __ASSEMBLY__ */

/*
 * Since there is no objtool in RHEL6, the .discard.nospec object section
 * is not generated.
 */
#define ANNOTATE_NOSPEC_ALTERNATIVE
#if 0
	"999:\n\t"						\
	".pushsection .discard.nospec\n\t"			\
	".long 999b - .\n\t"					\
	".popsection\n\t"
#endif

#if defined(CONFIG_X86_64) && defined(RETPOLINE)

/*
 * Since the inline asm uses the %V modifier which is only in newer GCC,
 * the 64-bit one is dependent on RETPOLINE not CONFIG_RETPOLINE.
 */
# define CALL_NOSPEC						\
	ANNOTATE_NOSPEC_ALTERNATIVE				\
	ALTERNATIVE(						\
	"call *%[thunk_target]\n",				\
	"call __x86_indirect_thunk_%V[thunk_target]\n",		\
	X86_FEATURE_RETPOLINE)
# define THUNK_TARGET(addr) [thunk_target] "r" (addr)

#elif defined(CONFIG_X86_32) && defined(CONFIG_RETPOLINE)
/*
 * For i386 we use the original ret-equivalent retpoline, because
 * otherwise we'll run out of registers. We don't care about CET
 * here, anyway.
 */
# define CALL_NOSPEC ALTERNATIVE("call *%[thunk_target]\n",	\
	"       jmp    904f;\n"					\
	"       .align 16\n"					\
	"901:	call   903f;\n"					\
	"902:	pause;\n"					\
	"    	lfence;\n"					\
	"       jmp    902b;\n"					\
	"       .align 16\n"					\
	"903:	addl   $4, %%esp;\n"				\
	"       pushl  %[thunk_target];\n"			\
	"       ret;\n"						\
	"       .align 16\n"					\
	"904:	call   901b;\n",				\
	X86_FEATURE_RETPOLINE)

# define THUNK_TARGET(addr) [thunk_target] "rm" (addr)
#else /* No retpoline for C / inline asm */
# define CALL_NOSPEC "call *%[thunk_target]\n"
# define THUNK_TARGET(addr) [thunk_target] "rm" (addr)
#endif

/* The Spectre V2 mitigation variants */
enum spectre_v2_mitigation {
	SPECTRE_V2_NONE,
	SPECTRE_V2_RETPOLINE_MINIMAL,
	SPECTRE_V2_RETPOLINE_MINIMAL_AMD,
	SPECTRE_V2_RETPOLINE_NO_IBPB,
	SPECTRE_V2_RETPOLINE_AMD,
	SPECTRE_V2_RETPOLINE_UNSAFE_MODULE,
	SPECTRE_V2_RETPOLINE,
	SPECTRE_V2_RETPOLINE_IBRS_USER,
	SPECTRE_V2_IBRS,
	SPECTRE_V2_IBRS_ALWAYS,
	SPECTRE_V2_IBP_DISABLED,
};

/*
 * asm(_ASM_SP) doesn't work as the RHEL6 gcc compiler seems to have
 * problem with exact spaces.
 */
#ifdef CONFIG_X86_64
#define _ASM_STACK_POINTER	"rsp"
#else
#define _ASM_STACK_POINTER	"esp"
#endif

/*
 * The Intel specification for the SPEC_CTRL MSR requires that we
 * preserve any already set reserved bits at boot time (e.g. for
 * future additions that this kernel is not currently aware of).
 * We then set any additional mitigation bits that we want
 * ourselves and always use this as the base for SPEC_CTRL.
 * We also use this when handling guest entry/exit as below.
 */
extern u64 x86_spec_ctrl_base;

/* The Speculative Store Bypass disable variants */
enum ssb_mitigation {
	SPEC_STORE_BYPASS_NONE,
	SPEC_STORE_BYPASS_DISABLE,
	SPEC_STORE_BYPASS_PRCTL,
	SPEC_STORE_BYPASS_SECCOMP,
};

/* AMD specific Speculative Store Bypass MSR data */
extern u64 x86_amd_ls_cfg_base;
extern u64 x86_amd_ls_cfg_ssbd_mask;

/*
 * On VMEXIT we must ensure that no RSB predictions learned in the guest
 * can be followed in the host, by overwriting the RSB completely. Both
 * retpoline and IBRS mitigations for Spectre v2 need this; only on future
 * CPUs with IBRS_ATT *might* it be avoided.
 */
static inline void fill_RSB(void)
{
	unsigned long loops;
	register unsigned long sp asm(_ASM_STACK_POINTER);

	asm volatile (__stringify(__FILL_RETURN_BUFFER(%0, RSB_CLEAR_LOOPS, %1))
		      : "=r" (loops), "+r" (sp)
		      : : "memory" );
}

extern enum spectre_v2_mitigation spectre_v2_get_mitigation(void);
extern void spectre_v2_set_mitigation(enum spectre_v2_mitigation mode);
extern void spectre_v2_retpoline_reset(void);
extern void __spectre_v2_select_mitigation(void);
extern void spectre_v2_print_mitigation(void);
extern bool spectre_v2_has_full_retpoline(void);

extern bool mds_idle_clear;

#include <asm/segment.h>

/**
 * mds_clear_cpu_buffers - Mitigation for MDS vulnerability
 *
 * This uses the otherwise unused and obsolete VERW instruction in
 * combination with microcode which triggers a CPU buffer flush when the
 * instruction is executed.
 */
static inline void mds_clear_cpu_buffers(void)
{
	static const u16 ds = __KERNEL_DS;

	/*
	 * Has to be the memory-operand variant because only that
	 * guarantees the CPU buffer flush functionality according to
	 * documentation. The register-operand variant does not.
	 * Works with any segment selector, but a valid writable
	 * data segment is the fastest variant.
	 *
	 * "cc" clobber is required because VERW modifies ZF.
	 */
	asm volatile("verw %[ds]" : : [ds] "m" (ds) : "cc");
}

/**
 * mds_idle_clear_cpu_buffers - Mitigation for MDS vulnerability
 *
 * Clear CPU buffers if the corresponding static key is enabled
 */
static inline void mds_idle_clear_cpu_buffers(void)
{
	if (unlikely(mds_idle_clear))
		mds_clear_cpu_buffers();
}

#endif /* __ASSEMBLY__ */
#endif /* __NOSPEC_BRANCH_H__ */
