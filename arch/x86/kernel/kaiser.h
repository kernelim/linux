#ifdef CONFIG_PAGE_TABLE_ISOLATION

#include <asm/processor-flags.h>
#include <asm/kaiser.h>

/* KAISER PGDs are 8k.  Flip bit 12 to switch between the two halves: */
#define KAISER_SWITCH_MASK (1<<PAGE_SHIFT)
#define KAISER_SWITCH_MASK_PCID (KAISER_SWITCH_MASK | KAISER_SHADOW_PCID_ASID)

.macro ADJUST_KERNEL_CR3 reg:req
	/* Clear "KAISER bit", point CR3 at kernel pagetables: */
	andq	$(~KAISER_SWITCH_MASK), \reg
.endm

.macro ADJUST_KERNEL_CR3_PCID reg:req
	bts	$X86_CR3_PCID_NOFLUSH_BIT, \reg
	/* Clear "KAISER bit", point CR3 at kernel pagetables: */
	andq	$(~KAISER_SWITCH_MASK_PCID), \reg
.endm

.macro ADJUST_USER_CR3 reg:req
	/* Move CR3 up a page to the user page tables: */
	orq	$KAISER_SWITCH_MASK, \reg
.endm

.macro ADJUST_USER_CR3_PCID reg:req
	bts	$X86_CR3_PCID_NOFLUSH_BIT, \reg
	/* Move CR3 up a page to the user page tables: */
	orq	$KAISER_SWITCH_MASK_PCID, \reg
.endm

.macro SWITCH_TO_KERNEL_CR3
	testl   $KAISER_PCP_ENABLED, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lnokaiser_\@

	movq    %rax, PER_CPU_VAR(kaiser_scratch)
	movq	%cr3, %rax

	testl   $KAISER_PCP_PCID, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lkaiser_nopcid_\@

	ADJUST_KERNEL_CR3_PCID %rax
	movq	%rax, %cr3
	movq	PER_CPU_VAR(kaiser_scratch), %rax
	jmp      .Lnokaiser_\@

.Lkaiser_nopcid_\@:
	ADJUST_KERNEL_CR3 %rax
	movq	%rax, %cr3
	movq	PER_CPU_VAR(kaiser_scratch), %rax

.Lnokaiser_\@:
.endm

.macro SWITCH_TO_USER_CR3
	testl   $KAISER_PCP_ENABLED, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lnokaiser_\@

	movq    %rax, PER_CPU_VAR(kaiser_scratch)
	movq	%cr3, %rax

	testl   $KAISER_PCP_PCID, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lkaiser_nopcid_\@

	ADJUST_USER_CR3_PCID %rax
	movq	%rax, %cr3
	movq	PER_CPU_VAR(kaiser_scratch), %rax
	jmp      .Lnokaiser_\@

.Lkaiser_nopcid_\@:
	ADJUST_USER_CR3 %rax
	movq	%rax, %cr3
	movq	PER_CPU_VAR(kaiser_scratch), %rax

.Lnokaiser_\@:
.endm

.macro SAVE_AND_SWITCH_TO_KERNEL_CR3 scratch_reg:req save_reg:req
	movq	%cr3, \save_reg

	testl   $KAISER_PCP_ENABLED, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lnokaiser_\@

	movq	\save_reg, \scratch_reg
	/*
	 * Is the switch bit zero?  This means the address is
	 * up in real KAISER patches in a moment.
	 */
	testq	$KAISER_SWITCH_MASK, \scratch_reg
	jz	.Lnokaiser_\@

	testl   $KAISER_PCP_PCID, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lkaiser_nopcid_\@

	ADJUST_KERNEL_CR3_PCID \scratch_reg
	jmp      .Ldone_\@

.Lkaiser_nopcid_\@:
	ADJUST_KERNEL_CR3 \scratch_reg
.Ldone_\@:
	movq	\scratch_reg, %cr3

.Lnokaiser_\@:
.endm

.macro RESTORE_CR3 scratch_reg:req save_reg:req
	testl   $KAISER_PCP_ENABLED, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lnokaiser_\@

	movq	%cr3, \scratch_reg
	testq \save_reg, \scratch_reg
	je .Lnokaiser_\@
	testl   $KAISER_PCP_PCID, PER_CPU_VAR(kaiser_enabled_pcp)
	jz      .Lkaiser_nopcid_\@
	bts	$X86_CR3_PCID_NOFLUSH_BIT, \save_reg
.Lkaiser_nopcid_\@:
	movq	\save_reg, %cr3

.Lnokaiser_\@:
.endm

#else /* CONFIG_PAGE_TABLE_ISOLATION=n: */

.macro SWITCH_TO_KERNEL_CR3
.endm
.macro SWITCH_TO_USER_CR3
.endm
.macro SAVE_AND_SWITCH_TO_KERNEL_CR3 scratch_reg:req save_reg:req
.endm
.macro RESTORE_CR3 scratch_reg:req save_reg:req
.endm

#endif
