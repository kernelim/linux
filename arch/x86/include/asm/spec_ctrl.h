#ifndef _ASM_X86_SPEC_CTRL_H
#define _ASM_X86_SPEC_CTRL_H

#ifdef __ASSEMBLY__

#include <asm/msr-index.h>

#define IBRS_ENTRY_PCP		PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_entry)
#define IBRS_EXIT_PCP		PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_exit)
#define IBRS_HI32_PCP		PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_hi32)

/*
 * The BIT() macro is a shift by 1UL, and it is used as part of the
 * SPEC_CTRL_IBRS macro.  Older assemblers (prior to binutils 2.28) do
 * not accept the L or LL suffixes, however.  Redefine BIT here in a
 * way that will work with the older toolchains.
 */
#undef BIT
#define BIT(nr) (_AC(1,UL) << (nr))

.macro __IBRS_ENTRY
	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl IBRS_HI32_PCP, %edx
	movl IBRS_ENTRY_PCP, %eax
	wrmsr
.endm

.macro IBRS_ENTRY
	ALTERNATIVE "jmp .Lend_\@", "", X86_FEATURE_SPEC_CTRL_ENTRY
	push %_ASM_AX
	push %_ASM_CX
	push %_ASM_DX
	__IBRS_ENTRY
	pop  %_ASM_DX
	pop  %_ASM_CX
	pop  %_ASM_AX
	jmp  .Lend_\@

.Lend_\@:
.endm

.macro IBRS_ENTRY_CLOBBER
	ALTERNATIVE "jmp .Lend_\@", "", X86_FEATURE_SPEC_CTRL_ENTRY
	__IBRS_ENTRY

.Lend_\@:
.endm

.macro IBRS_ENTRY_SAVE_AND_CLOBBER save_reg:req
	ALTERNATIVE "jmp .Lend_\@", "", X86_FEATURE_SPEC_CTRL_ENTRY

	movl $MSR_IA32_SPEC_CTRL, %ecx
	rdmsr
	movl %eax, \save_reg
	__IBRS_ENTRY

.Lend_\@:
.endm

.macro __IBRS_EXIT
	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl IBRS_HI32_PCP, %edx
	movl IBRS_EXIT_PCP, %eax
	wrmsr
.endm

.macro IBRS_EXIT
	ALTERNATIVE "jmp .Lend_\@", "", X86_FEATURE_SPEC_CTRL_EXIT

	push %_ASM_AX
	push %_ASM_CX
	push %_ASM_DX
	__IBRS_EXIT
	pop  %_ASM_DX
	pop  %_ASM_CX
	pop  %_ASM_AX

.Lend_\@:
.endm

.macro IBRS_EXIT_CLOBBER
	ALTERNATIVE "jmp .Lend_\@", "", X86_FEATURE_SPEC_CTRL_EXIT
	__IBRS_EXIT

.Lend_\@:
.endm

/*
 * The IBRS_EXIT_RESTORE_CLOBBER must match the corresponding
 * IBRS_ENTRY_SAVE_AND_CLOBBER macro and so should use
 * X86_FEATURE_SPEC_CTRL_ENTRY feature bit.
 */
.macro IBRS_EXIT_RESTORE_CLOBBER save_reg:req
	ALTERNATIVE "jmp .Lend_\@", "", X86_FEATURE_SPEC_CTRL_ENTRY
	/*
	 * If the IBRS bit is on in \save_reg, there is no need to
	 * rewrite the SPEC_CTRL MSR.
	 */
	andl $SPEC_CTRL_IBRS, \save_reg
	jnz  .Lend_\@
	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl IBRS_HI32_PCP, %edx
	movl \save_reg, %eax
	wrmsr

.Lend_\@:
.endm

#else  /* __ASSEMBLY__ */

#include <linux/percpu.h>
#include <asm/nospec-branch.h>
#include <asm/microcode.h>

/*
 * Percpu IBRS kernel entry/exit control structure
 */
struct kernel_ibrs_spec_ctrl {
	union {
		struct {
			/*
			 * The lower and upper 32-bit of SPEC_CTRL MSR
			 * when entering kernel.
			 */
			unsigned int entry;
			unsigned int hi32;
		};
		u64	entry64;	/* Full 64-bit SPEC_CTRL MSR */
	};
	unsigned int exit;	/* Lower 32-bit of SPEC_CTRL MSR for exit */
};

DECLARE_PER_CPU(struct kernel_ibrs_spec_ctrl, spec_ctrl_pcp);

extern void spec_ctrl_init(void);
extern void spec_ctrl_cpu_init(void);
extern void spec_ctrl_update(u64 spec_ctrl);
extern void spec_ctrl_smt_update(void);
extern bool spec_ctrl_enable_ibrs(void);
extern bool spec_ctrl_enable_ibrs_always(void);
extern bool spec_ctrl_enable_retpoline_ibrs_user(void);
extern bool is_skylake_era(void);

enum {
	IBRS_DISABLED = 0,

	/* In kernel, disabled in userland */
	IBRS_ENABLED,

	/* In both kernel and userland */
	IBRS_ENABLED_ALWAYS,

	/* In userland, disabled in kernel */
	IBRS_ENABLED_USER,

	IBRS_MAX = IBRS_ENABLED_USER,
};

static __always_inline bool cpu_has_ibrs(void)
{
	return boot_cpu_has(X86_FEATURE_IBRS);
}

#endif /* __ASSEMBLY__ */
#endif /* _ASM_X86_SPEC_CTRL_H */
