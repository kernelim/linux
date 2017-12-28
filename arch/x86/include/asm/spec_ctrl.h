#ifndef _ASM_X86_SPEC_CTRL_H
#define _ASM_X86_SPEC_CTRL_H

#define SPEC_CTRL_PCP_IBRS	(1<<0)
#define SPEC_CTRL_PCP_IBPB	(1<<1)
#define SPEC_CTRL_PCP_IBRS_USER	(1<<2)
#define SPEC_CTRL_PCP_ONLY_IBPB	(1<<3) /* use IBPB instead of IBRS */

#define SPEC_CTRL_PCP_ENTRY (SPEC_CTRL_PCP_IBRS|SPEC_CTRL_PCP_ONLY_IBPB)

#ifdef __ASSEMBLY__

#include <asm/msr-index.h>
#include <asm/alternative-asm.h>
#include <asm/cpufeature.h>
#include <asm/nops.h>

.macro ENABLE_IBRS
	testl $SPEC_CTRL_PCP_ENTRY, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@


	pushq %rax
	pushq %rcx
	pushq %rdx
	movl $0, %edx
	testl $SPEC_CTRL_PCP_ONLY_IBPB, PER_CPU_VAR(spec_ctrl_pcp)
	jnz .Lonly_ibpb_\@
	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl $FEATURE_ENABLE_IBRS, %eax
.Lback_\@:
	wrmsr
	popq %rdx
	popq %rcx
	popq %rax
	jmp .Lend_\@

.Lonly_ibpb_\@:
	movl $MSR_IA32_PRED_CMD, %ecx
	movl $FEATURE_SET_IBPB, %eax
	jmp .Lback_\@

.Lskip_\@:
	lfence
.Lend_\@:
.endm

.macro ENABLE_IBRS_CLOBBER
	testl $SPEC_CTRL_PCP_ENTRY, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@

	movl $0, %edx
	testl $SPEC_CTRL_PCP_ONLY_IBPB, PER_CPU_VAR(spec_ctrl_pcp)
	jnz .Lonly_ibpb_\@
	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl $FEATURE_ENABLE_IBRS, %eax
.Lback_\@:
	wrmsr
	jmp .Lend_\@

.Lonly_ibpb_\@:
	movl $MSR_IA32_PRED_CMD, %ecx
	movl $FEATURE_SET_IBPB, %eax
	jmp .Lback_\@

.Lskip_\@:
	lfence
.Lend_\@:
.endm

.macro ENABLE_IBRS_SAVE_AND_CLOBBER save_reg:req
	testl $SPEC_CTRL_PCP_ENTRY, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@

	testl $SPEC_CTRL_PCP_ONLY_IBPB, PER_CPU_VAR(spec_ctrl_pcp)
	jnz .Lonly_ibpb_\@

	movl $MSR_IA32_SPEC_CTRL, %ecx
	rdmsr
	movl %eax, \save_reg

	movl $0, %edx
	movl $FEATURE_ENABLE_IBRS, %eax
	wrmsr
	jmp .Lend_\@

.Lonly_ibpb_\@:
	movl $0, %edx
	movl $MSR_IA32_PRED_CMD, %ecx
	movl $FEATURE_SET_IBPB, %eax
	wrmsr

	/*
	 * Simulate no IBRS just in case IBRS is enabled in the middle
	 * of an exception, this avoids the very remote risk of
	 * writing random save_reg content into the SPEC_CTRL MSR in
	 * such case.
	 */
	movl $FEATURE_ENABLE_IBRS, \save_reg

	jmp .Lend_\@

.Lskip_\@:
	/*
	 * Simulate no IBRS just in case IBRS is enabled in the middle
	 * of an exception, this avoids the very remote risk of
	 * writing random save_reg content into the SPEC_CTRL MSR in
	 * such case.
	 */
	movl $FEATURE_ENABLE_IBRS, \save_reg

	lfence
.Lend_\@:
.endm

.macro DISABLE_IBRS
	testl $SPEC_CTRL_PCP_IBRS, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@

	pushq %rax
	pushq %rcx
	pushq %rdx
	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl $0, %edx
	movl $0, %eax
	wrmsr
	popq %rdx
	popq %rcx
	popq %rax

.Lskip_\@:
.endm

.macro RESTORE_IBRS_CLOBBER save_reg:req
	testl $SPEC_CTRL_PCP_IBRS, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@

	cmpl $FEATURE_ENABLE_IBRS, \save_reg
	je .Lskip_\@

	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl $0, %edx
	movl \save_reg, %eax
	wrmsr

.Lskip_\@:
.endm

.macro DISABLE_IBRS_CLOBBER
	testl $SPEC_CTRL_PCP_IBRS, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@

	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl $0, %edx
	movl $0, %eax
	wrmsr

.Lskip_\@:
.endm

#if 0 /* unused */
.macro SET_IBPB
	testl $SPEC_CTRL_PCP_IBPB, PER_CPU_VAR(spec_ctrl_pcp)
	jz .Lskip_\@

	pushq %rax
	pushq %rcx
	pushq %rdx
	movl $MSR_IA32_PRED_CMD, %ecx
	movl $0, %edx
	movl $FEATURE_SET_IBPB, %eax
	wrmsr
	popq %rdx
	popq %rcx
	popq %rax

.Lskip_\@:
.endm
#endif

#define __STUFF_RSB				\
	call	1f;				\
	pause;					\
1:	call	2f;				\
	pause;					\
2:	call	3f;				\
	pause;					\
3:	call	4f;				\
	pause;					\
4:	call	5f;				\
	pause;					\
5:	call	6f;				\
	pause;					\
6:	call	7f;				\
	pause;					\
7:	call	8f;				\
	pause;					\
8:	call	9f;				\
	pause;					\
9:	call	10f;				\
	pause;					\
10:	call	11f;				\
	pause;					\
11:	call	12f;				\
	pause;					\
12:	call	13f;				\
	pause;					\
13:	call	14f;				\
	pause;					\
14:	call	15f;				\
	pause;					\
15:	call	16f;				\
	pause;					\
16:	call	17f;				\
	pause;					\
17:	call	18f;				\
	pause;					\
18:	call	19f;				\
	pause;					\
19:	call	20f;				\
	pause;					\
20:	call	21f;				\
	pause;					\
21:	call	22f;				\
	pause;					\
22:	call	23f;				\
	pause;					\
23:	call	24f;				\
	pause;					\
24:	call	25f;				\
	pause;					\
25:	call	26f;				\
	pause;					\
26:	call	27f;				\
	pause;					\
27:	call	28f;				\
	pause;					\
28:	call	29f;				\
	pause;					\
29:	call	30f;				\
	pause;					\
30:	call	31f;				\
	pause;					\
31:	call	32f;				\
	pause;					\
32:						\
	add $(32*8), %rsp

/* 131 bytes / 7 = 33 ASM_NOP7 */
#define __STUFF_RSB_NOP						\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7;	\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7;	\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7;	\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7;	\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7;	\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7; ASM_NOP7;	\
	 ASM_NOP7; ASM_NOP7; ASM_NOP7

/*
 * Forward and backward jump over STFF_RSB with local numeric labels is not
 * safe.
 */
#define STUFF_RSB							\
	661: __STUFF_RSB; 663:						\
	.pushsection .altinstr_replacement, "ax" ;			\
	662: __STUFF_RSB_NOP; 664:					\
	.popsection ;							\
	.pushsection .altinstructions, "a" ;				\
	altinstruction_entry 661b, 662b, X86_FEATURE_SMEP, 663b-661b, 664b-662b; \
	.popsection

.macro CLEAR_R8_TO_R15
	xorq %r15, %r15
	xorq %r14, %r14
	xorq %r13, %r13
	xorq %r12, %r12
	xorq %r11, %r11
	xorq %r10, %r10
	xorq %r9, %r9
	xorq %r8, %r8
.endm

.macro CLEAR_EXTRA_REGS
	xorq %r15, %r15
	xorq %r14, %r14
	xorq %r13, %r13
	xorq %r12, %r12
	xorq %rbp, %rbp
	xorq %rbx, %rbx
.endm

#else /* __ASSEMBLY__ */

#include <linux/ptrace.h>
#include <asm/microcode.h>
#include <asm/thread_info.h>

#ifdef CONFIG_SPEC_CTRL
extern void set_spec_ctrl_pcp_ibrs(bool enable);
extern void set_spec_ctrl_pcp_ibpb(bool enable);

extern void spec_ctrl_rescan_cpuid(void);
extern void spec_ctrl_init(struct cpuinfo_x86 *c);
extern void spec_ctrl_cpu_init(void);

static inline int cpu_has_spec_ctrl(void)
{
	if (boot_cpu_has(X86_FEATURE_SPEC_CTRL))
		return 1;

	/* rmb to prevent wrong speculation for security */
	rmb();
	return 0;
}

static __always_inline void __spec_ctrl_vm_ibrs(u64 vcpu_ibrs, bool vmenter)
{
	u64 host_ibrs = 0;
	if (percpu_read(spec_ctrl_pcp) & (SPEC_CTRL_PCP_IBRS_USER |
					      SPEC_CTRL_PCP_IBRS)) {
		/*
		 * If IBRS is enabled for host kernel mode or
		 * host user mode we must set
		 * FEATURE_ENABLE_IBRS at vmexit.
		 */
		host_ibrs = FEATURE_ENABLE_IBRS;
	}
	else
		/* rmb to prevent wrong speculation for security */
		rmb();

	if (vcpu_ibrs != host_ibrs)
		native_wrmsrl(MSR_IA32_SPEC_CTRL,
			      vmenter ? vcpu_ibrs : host_ibrs);
}

static inline void spec_ctrl_vmenter_ibrs(u64 vcpu_ibrs)
{
	if (cpu_has_spec_ctrl())
		__spec_ctrl_vm_ibrs(vcpu_ibrs, true);
}

static inline void __spec_ctrl_vmexit_ibrs(u64 vcpu_ibrs)
{
	__spec_ctrl_vm_ibrs(vcpu_ibrs, false);
}

static inline void spec_ctrl_enable_ibrs(void)
{
	if (cpu_has_spec_ctrl()) {
		if (percpu_read(spec_ctrl_pcp) & SPEC_CTRL_PCP_IBRS)
			native_wrmsrl(MSR_IA32_SPEC_CTRL, FEATURE_ENABLE_IBRS);
		else
			/* rmb to prevent wrong speculation for security */
			rmb();
	}
}

static inline void spec_ctrl_disable_ibrs(void)
{
	if (cpu_has_spec_ctrl()) {
		if (percpu_read(spec_ctrl_pcp) & SPEC_CTRL_PCP_IBRS)
			native_wrmsrl(MSR_IA32_SPEC_CTRL, 0);
		else
			/* rmb to prevent wrong speculation for security */
			rmb();
	}
}

static inline void __spec_ctrl_ibpb(void)
{
	native_wrmsrl(MSR_IA32_PRED_CMD, FEATURE_SET_IBPB);
}

static inline void spec_ctrl_ibpb(void)
{
	if (boot_cpu_has(X86_FEATURE_IBPB_SUPPORT)) {
		if (percpu_read(spec_ctrl_pcp) & SPEC_CTRL_PCP_IBPB)
			__spec_ctrl_ibpb();
	}
}

static inline int spec_ctrl_check_only_ibpb(void)
{
	if (boot_cpu_has(X86_FEATURE_IBPB_SUPPORT) &&
	    percpu_read(spec_ctrl_pcp) & (SPEC_CTRL_PCP_ONLY_IBPB))
		return 1;

	/* rmb to prevent wrong speculation for security */
	rmb();
	return 0;
}

static inline void spec_ctrl_ibpb_as_ibrs(void)
{
	if (spec_ctrl_check_only_ibpb())
		__spec_ctrl_ibpb();
}

static inline void spec_ctrl_ibpb_if_different_creds(struct task_struct *next)
{
	struct task_struct *prev = current;

	if (boot_cpu_has(X86_FEATURE_IBPB_SUPPORT)) {
		if (percpu_read(spec_ctrl_pcp) & SPEC_CTRL_PCP_IBPB && next &&
		    ___ptrace_may_access(next, NULL, prev, PTRACE_MODE_IBPB))
			__spec_ctrl_ibpb();
	}
}

static __always_inline void stuff_RSB(void)
{
	spec_ctrl_ibpb_as_ibrs();
	__asm__ __volatile__("       call 1f; pause;"
			     "1:     call 2f; pause;"
			     "2:     call 3f; pause;"
			     "3:     call 4f; pause;"
			     "4:     call 5f; pause;"
			     "5:     call 6f; pause;"
			     "6:     call 7f; pause;"
			     "7:     call 8f; pause;"
			     "8:     call 9f; pause;"
			     "9:     call 10f; pause;"
			     "10:    call 11f; pause;"
			     "11:    call 12f; pause;"
			     "12:    call 13f; pause;"
			     "13:    call 14f; pause;"
			     "14:    call 15f; pause;"
			     "15:    call 16f; pause;"
			     "16:    call 17f; pause;"
			     "17:    call 18f; pause;"
			     "18:    call 19f; pause;"
			     "19:    call 20f; pause;"
			     "20:    call 21f; pause;"
			     "21:    call 22f; pause;"
			     "22:    call 23f; pause;"
			     "23:    call 24f; pause;"
			     "24:    call 25f; pause;"
			     "25:    call 26f; pause;"
			     "26:    call 27f; pause;"
			     "27:    call 28f; pause;"
			     "28:    call 29f; pause;"
			     "29:    call 30f; pause;"
			     "30:    call 31f; pause;"
			     "31:    call 32f; pause;"
			     "32:    add $(32*8), %%rsp": : :"memory");
}

#else /* CONFIG_SPEC_CTRL */

static inline void set_spec_ctrl_pcp_ibrs(bool enable)	{ }
static inline void set_spec_ctrl_pcp_ibpb(bool enable)	{ }
static inline void spec_ctrl_enable_ibrs (void)		{ }
static inline void spec_ctrl_disable_ibrs(void)		{ }
static inline void spec_ctrl_ibpb	 (void)		{ }
static inline void __spec_ctrl_ibpb	 (void)		{ }
static inline void stuff_RSB		 (void)		{ }
static inline void spec_ctrl_rescan_cpuid(void)		{ }
static inline void spec_ctrl_cpu_init	 (void)		{ }

static inline void spec_ctrl_vmenter_ibrs (u64 vcpu_ibrs) { }
static inline void __spec_ctrl_vmexit_ibrs(u64 vcpu_ibrs) { }
static inline void __spec_ctrl_vm_ibrs	  (u64 vcpu_ibrs, bool vmenter) { }
static inline void spec_ctrl_init	  (struct cpuinfo_x86 *c) { }
static inline int  cpu_has_spec_ctrl	  (void) { return 0; }

static inline void spec_ctrl_ibpb_if_different_creds(struct task_struct *next)
	{ }

#endif /* CONFIG_SPEC_CTRL */

#endif /* __ASSEMBLY__ */
#endif /* _ASM_X86_SPEC_CTRL_H */
