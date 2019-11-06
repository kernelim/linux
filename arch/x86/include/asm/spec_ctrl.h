#ifndef _ASM_X86_SPEC_CTRL_H
#define _ASM_X86_SPEC_CTRL_H

#define SPEC_CTRL_PCP_IBRS_ENTRY	(1<<0)
#define SPEC_CTRL_PCP_IBRS_EXIT 	(1<<1)

#define SPEC_CTRL_PCP_IBRS (SPEC_CTRL_PCP_IBRS_ENTRY|SPEC_CTRL_PCP_IBRS_EXIT)

#ifdef __ASSEMBLY__

#include <asm/msr-index.h>
#include <asm/alternative-asm.h>
#include <asm/cpufeature.h>
#include <asm/nops.h>

#define IBRS_ENABLED_PCP	PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_enabled)
#define IBRS_ENTRY_PCP		PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_entry)
#define IBRS_EXIT_PCP		PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_exit)
#define IBRS_HI32_PCP		PER_CPU_VAR(spec_ctrl_pcp + \
				KERNEL_IBRS_SPEC_CTRL_hi32)
/*
 * For old 32-bit AMD Athlons that lack SSE2, lfence is also not supported.
 * As stated in AMD64 Architecture Programmer’s Manual Volume 3, 3.10
 * (Feb 2005), "Support for the LFENCE instruction is indicated when the
 * SSE2 bit (bit 26) is set to 1 in EDX after executing CPUID standard
 * function 1."
 *
 * It is safe to patch out lfence in this case as there will be limited
 * speculative execution and retpoline should have been enabled.
 */
#ifdef CONFIG_X86_32
#define LFENCE	ALTERNATIVE	"", "lfence", X86_FEATURE_XMM2
#else
#define LFENCE	lfence
#endif

.macro __IBRS_ENTRY
	movl IBRS_HI32_PCP, %edx
	movl IBRS_ENTRY_PCP, %eax
	movl $MSR_IA32_SPEC_CTRL, %ecx
	wrmsr
.endm

.macro IBRS_ENTRY
	testl $SPEC_CTRL_PCP_IBRS_ENTRY, IBRS_ENABLED_PCP
	jz .Lskip_\@

	push %_ASM_AX
	push %_ASM_CX
	push %_ASM_DX
	__IBRS_ENTRY
	pop %_ASM_DX
	pop %_ASM_CX
	pop %_ASM_AX
	jmp .Lend_\@

.Lskip_\@:
	LFENCE
.Lend_\@:
.endm

.macro IBRS_ENTRY_CLOBBER
	testl $SPEC_CTRL_PCP_IBRS_ENTRY, IBRS_ENABLED_PCP
	jz .Lskip_\@

	__IBRS_ENTRY
	jmp .Lend_\@

.Lskip_\@:
	LFENCE
.Lend_\@:
.endm

#define NO_IBRS_RESTORE		(-1)	/* No restore on exit */

/*
 * The save_reg is initialize to NO_IBRS_RESTORE just in case IBRS is
 * enabled in the middle of an exception, this avoids the very remote risk
 * of writing random save_reg content into the SPEC_CTRL MSR in such case.
 */
.macro IBRS_ENTRY_SAVE_AND_CLOBBER save_reg:req
	movl $NO_IBRS_RESTORE, \save_reg
	testl $SPEC_CTRL_PCP_IBRS_ENTRY, IBRS_ENABLED_PCP
	jz .Lskip_\@

	movl $MSR_IA32_SPEC_CTRL, %ecx
	rdmsr

	/*
	 * If the content of the MSR matches the kernel entry value,
	 * we should still rewrite the MSR anyway to enforce the
	 * barrier-like semantics in some IBRS implementations.
	 * Nowever, we can leave the save_reg as NO_IBRS_RESTORE
	 * so that we won't do a rewrite on exit,
	 *
	 * %edx is initialized by rdmsr above, and so it doesn't need
	 * to be touched.
	 */
	movl IBRS_ENTRY_PCP, %ecx
	cmpl %eax, %ecx
	je   .Lwrmsr_\@

	movl %eax, \save_reg
.Lwrmsr_\@:
	movl $MSR_IA32_SPEC_CTRL, %ecx
	wrmsr
	jmp  .Lend_\@

.Lskip_\@:
	LFENCE
.Lend_\@:
.endm

.macro __IBRS_EXIT
	movl IBRS_HI32_PCP, %edx
	movl IBRS_EXIT_PCP, %eax
	movl $MSR_IA32_SPEC_CTRL, %ecx
	wrmsr
.endm

.macro IBRS_EXIT
	testl $SPEC_CTRL_PCP_IBRS_EXIT, IBRS_ENABLED_PCP
	jz .Lskip_\@

	push %_ASM_AX
	push %_ASM_CX
	push %_ASM_DX
	__IBRS_EXIT
	pop %_ASM_DX
	pop %_ASM_CX
	pop %_ASM_AX

.Lskip_\@:
.endm

.macro IBRS_EXIT_RESTORE_CLOBBER save_reg:req
	testl $SPEC_CTRL_PCP_IBRS, IBRS_ENABLED_PCP
	jz .Lskip_\@

	cmpl $NO_IBRS_RESTORE, \save_reg
	je  .Lskip_\@

	movl $MSR_IA32_SPEC_CTRL, %ecx
	movl IBRS_HI32_PCP, %edx
	movl \save_reg, %eax
	wrmsr

.Lskip_\@:
.endm

.macro IBRS_EXIT_CLOBBER
	testl $SPEC_CTRL_PCP_IBRS_EXIT, IBRS_ENABLED_PCP
	jz .Lskip_\@

	__IBRS_EXIT

.Lskip_\@:
.endm

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

.macro CLEAR_R10_TO_R15
	xorq %r15, %r15
	xorq %r14, %r14
	xorq %r13, %r13
	xorq %r12, %r12
	xorq %r11, %r11
	xorq %r10, %r10
.endm

#else /* __ASSEMBLY__ */

#include <linux/ptrace.h>
#include <asm/microcode.h>
#include <asm/thread_info.h>
#include <asm/intel-family.h>
#include <asm/nospec-branch.h>

/*
 * Special SPEC_CTRL MSR value to write the content of the spec_ctrl_pcp.
 */
#define SPEC_CTRL_MSR_REFRESH	((unsigned)-1)

extern enum ssb_mitigation ssb_mode;

extern void spec_ctrl_rescan_cpuid(void);
extern void spec_ctrl_init(void);
extern void spec_ctrl_cpu_init(void);
extern void spec_ctrl_save_msr(void);
extern void ssb_select_mitigation(void);
extern void ssb_print_mitigation(void);
extern void mds_print_mitigation(void);
extern void taa_print_mitigation(void);

bool spec_ctrl_force_enable_ibrs(void);
bool spec_ctrl_cond_enable_ibrs(bool full_retpoline);
bool spec_ctrl_enable_ibrs_always(void);
bool spec_ctrl_force_enable_ibp_disabled(void);
bool spec_ctrl_cond_enable_ibp_disabled(void);
void spec_ctrl_enable_retpoline_ibrs_user(void);
void spec_ctrl_set_ssbd(bool ssbd_on);

bool unprotected_firmware_begin(void);
void unprotected_firmware_end(bool ibrs_on);

/*
 * Percpu IBRS kernel entry/exit control structure
 */
struct kernel_ibrs_spec_ctrl {
	unsigned int enabled;	/* Entry and exit enabled control bits */
	unsigned int exit;	/* Lower 32-bit of SPEC_CTRL MSR for exit */
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
};

DECLARE_PER_CPU_USER_MAPPED(struct kernel_ibrs_spec_ctrl, spec_ctrl_pcp);

/*
 * percpu_read() of a 64-bit variable isn't allowed in 32-bit build.
 */
#ifdef CONFIG_X86_64
static __always_inline u64 spec_ctrl_pcp_read64(void)
{
	return percpu_read(spec_ctrl_pcp.entry64);
}
#else /* CONFIG_X86_32 */
static __always_inline u64 spec_ctrl_pcp_read64(void)
{
	return (((u64)percpu_read(spec_ctrl_pcp.hi32)) << 32) |
		percpu_read(spec_ctrl_pcp.entry);
}
#endif

extern void x86_amd_ssbd_enable(void);

/* The Intel SPEC CTRL MSR base value cache */
extern u64 x86_spec_ctrl_base;
extern u64 x86_spec_ctrl_mask;

static inline u64 ssbd_tif_to_spec_ctrl(u64 tifn)
{
	BUILD_BUG_ON(TIF_SSBD < SPEC_CTRL_SSBD_SHIFT);
	return (tifn & _TIF_SSBD) >> (TIF_SSBD - SPEC_CTRL_SSBD_SHIFT);
}

static inline unsigned long ssbd_spec_ctrl_to_tif(u64 spec_ctrl)
{
	BUILD_BUG_ON(TIF_SSBD < SPEC_CTRL_SSBD_SHIFT);
	return (spec_ctrl & SPEC_CTRL_SSBD) << (TIF_SSBD - SPEC_CTRL_SSBD_SHIFT);
}

static inline u64 ssbd_tif_to_amd_ls_cfg(u64 tifn)
{
	return (tifn & _TIF_SSBD) ? x86_amd_ls_cfg_ssbd_mask : 0ULL;
}

static inline bool ssb_is_user_settable(unsigned int mode)
{
	return mode >= SPEC_STORE_BYPASS_PRCTL;
}

#ifdef CONFIG_SMP
extern void speculative_store_bypass_ht_init(void);
#else
static inline void speculative_store_bypass_ht_init(void) { }
#endif

extern void speculative_store_bypass_update(unsigned long tif);

static inline void speculative_store_bypass_update_current(void)
{
	speculative_store_bypass_update(current_thread_info()->flags);
}

enum {
	IBRS_DISABLED,

	/* in host kernel, disabled in guest and userland */
	IBRS_ENABLED,

	/* in host kernel and host userland, disabled in guest */
	IBRS_ENABLED_ALWAYS,

	/* in host userland, disabled in kernel and guest */
	IBRS_ENABLED_USER,

	IBRS_MAX = IBRS_ENABLED_USER,
};

static __always_inline int cpu_has_spec_ctrl(void)
{
	if (boot_cpu_has(X86_FEATURE_MSR_SPEC_CTRL))
		return 1;

	/* rmb to prevent wrong speculation for security */
	rmb();
	return 0;
}

static __always_inline bool ibrs_enabled_kernel(void)
{
	extern unsigned int ibrs_mode;

	return ibrs_mode == IBRS_ENABLED || ibrs_mode == IBRS_ENABLED_ALWAYS;
}

static inline bool retp_enabled(void)
{
	return boot_cpu_has(X86_FEATURE_RETPOLINE);
}

static inline bool ibpb_enabled(void)
{
	return (boot_cpu_has(X86_FEATURE_IBPB) &&
		(ibrs_enabled_kernel() || retp_enabled()));
}

/*
 * On VMENTER we must preserve whatever view of the SPEC_CTRL MSR
 * the guest has, while on VMEXIT we restore the kernel view. This
 * would be easier if SPEC_CTRL were architecturally maskable or
 * shadowable for guests but this is not (currently) the case.
 * Takes the guest view of SPEC_CTRL MSR as a parameter and also
 * the guest's version of VIRT_SPEC_CTRL, if emulated.
 */

static __always_inline void
x86_virt_spec_ctrl(u64 guest_spec_ctrl, u64 guest_virt_spec_ctrl, bool setguest)
{
	/*
	 * The per-cpu spec_ctrl_pcp.entry64 will be the SPEC_CTRL MSR value
	 * to be used in host kernel. This is performance critical code.
	 * Preemption is disabled, so we cannot race with sysfs writes.
	 */
	u64 msr, guestval, hostval = spec_ctrl_pcp_read64();
	struct thread_info *ti = current_thread_info();
	bool write_msr;

	if (boot_cpu_has(X86_FEATURE_MSR_SPEC_CTRL)) {
		/*
		 *  Restrict guest_spec_ctrl to supported values. Clear the
		 *  modifiable bits in the host base value and or the
		 *  modifiable bits from the guest value.
		 */
		guestval = hostval & ~x86_spec_ctrl_mask;
		guestval |= guest_spec_ctrl & x86_spec_ctrl_mask;

		/*
		 * IBRS may have barrier semantics so it must be set
		 * during vmexit (!setguest) if SPEC_CTRL MSR write is
		 * enabled at kernel entry.
		 */
		write_msr = (!setguest &&
			    (percpu_read(spec_ctrl_pcp.enabled) &
					   SPEC_CTRL_PCP_IBRS_ENTRY)) ||
			    (hostval != guestval);

		if (unlikely(write_msr)) {
			msr = setguest ? guestval : hostval;
			native_wrmsrl(MSR_IA32_SPEC_CTRL, msr);
		}
	}

	/*
	 * If SSBD is not handled in MSR_SPEC_CTRL on AMD, update
	 * MSR_AMD64_L2_CFG or MSR_VIRT_SPEC_CTRL if supported.
	 */
	if (!static_cpu_has(X86_FEATURE_LS_CFG_SSBD) &&
	    !static_cpu_has(X86_FEATURE_VIRT_SSBD))
		goto ret;

	/*
	 * If the SSBD mode is not user settable, grab the SSBD bit
	 * from x86_spec_ctrl_base. Otherwise, evaluate current's TIF_SSBD
	 * thread flag.
	 */
	if (!ssb_is_user_settable(READ_ONCE(ssb_mode)))
		hostval = x86_spec_ctrl_base & SPEC_CTRL_SSBD;
	else
		hostval = ssbd_tif_to_spec_ctrl(ti->flags);

	/* Sanitize the guest value */
	guestval = guest_virt_spec_ctrl & SPEC_CTRL_SSBD;

	if (hostval != guestval) {
		unsigned long tif;

		tif = setguest ? ssbd_spec_ctrl_to_tif(guestval) :
				 ssbd_spec_ctrl_to_tif(hostval);

		speculative_store_bypass_update(tif);
	}

ret:
	/* rmb not needed when entering guest */
	if (!setguest)
		/* rmb to prevent wrong speculation for security */
		rmb();
}

/**
 * x86_spec_ctrl_set_guest - Set speculation control registers for the guest
 * @guest_spec_ctrl:		The guest content of MSR_SPEC_CTRL
 * @guest_virt_spec_ctrl:	The guest controlled bits of MSR_VIRT_SPEC_CTRL
 *				(may get translated to MSR_AMD64_LS_CFG bits)
 *
 * Avoids writing to the MSR if the content/bits are the same
 */
static __always_inline void x86_spec_ctrl_set_guest(u64 guest_spec_ctrl,
						    u64 guest_virt_spec_ctrl)
{
	x86_virt_spec_ctrl(guest_spec_ctrl, guest_virt_spec_ctrl, true);
}

/**
 * x86_spec_ctrl_restore_host - Restore host speculation control registers
 * @guest_spec_ctrl:		The guest content of MSR_SPEC_CTRL
 * @guest_virt_spec_ctrl:	The guest controlled bits of MSR_VIRT_SPEC_CTRL
 *				(may get translated to MSR_AMD64_LS_CFG bits)
 *
 * Avoids writing to the MSR if the content/bits are the same
 */
static __always_inline void x86_spec_ctrl_restore_host(u64 guest_spec_ctrl,
						       u64 guest_virt_spec_ctrl)
{
	x86_virt_spec_ctrl(guest_spec_ctrl, guest_virt_spec_ctrl, false);
}

/*
 * The spec_ctrl_ibrs_off() is called before a cpu enters idle state and
 * spec_ctrl_ibrs_off() is called after exit from an idle state.
 */
static __always_inline void spec_ctrl_ibrs_on(void)
{
	if (ibrs_enabled_kernel()) {
		u64 spec_ctrl = spec_ctrl_pcp_read64();

		native_wrmsrl(MSR_IA32_SPEC_CTRL, spec_ctrl);
	} else {
		/* rmb to prevent wrong speculation for security */
		rmb();
	}
}

static __always_inline void spec_ctrl_ibrs_off(void)
{
	if (ibrs_enabled_kernel()) {
		u64 spec_ctrl = x86_spec_ctrl_base;

		/* SSBD controlled in MSR_SPEC_CTRL */
		if (static_cpu_has(X86_FEATURE_SPEC_CTRL_SSBD))
			spec_ctrl |= ssbd_tif_to_spec_ctrl(
					current_thread_info()->flags);

		native_wrmsrl(MSR_IA32_SPEC_CTRL, spec_ctrl);
	}
	/* rmb not needed when disabling IBRS */
}

/*
 * These functions are called before calling into firmware.  Firmware might
 * have indirect branches, so if we're running with retpolines, we need to
 * enable IBRS to protect the kernel from spectre v2.
 *
 * The 'ibrs_on' variable is used to prevent race conditions.  Otherwise, if
 * the admin disabled IBRS while a CPU was running in firmware, IBRS could get
 * stuck on indefinitely.
 *
 * There are still other race conditions possible, but they're generally not a
 * problem because they'll get corrected on the next kernel exit.
 */
static inline bool spec_ctrl_ibrs_on_firmware(void)
{
	bool ibrs_on = false;

	if (cpu_has_spec_ctrl() && retp_enabled() && !ibrs_enabled_kernel()) {
		u64 spec_ctrl = spec_ctrl_pcp_read64() | SPEC_CTRL_IBRS;

		native_wrmsrl(MSR_IA32_SPEC_CTRL, spec_ctrl);
		ibrs_on = true;
	} else {
		/* rmb to prevent wrong speculation for security */
		rmb();
	}

	return ibrs_on;
}

static inline void spec_ctrl_ibrs_off_firmware(bool ibrs_on)
{
	if (ibrs_on) {
		u64 spec_ctrl = spec_ctrl_pcp_read64();

		native_wrmsrl(MSR_IA32_SPEC_CTRL, spec_ctrl);
	} else {
		/* rmb to prevent wrong speculation for security */
		rmb();
	}
}

static inline void __spec_ctrl_ibpb(void)
{
	native_wrmsrl(MSR_IA32_PRED_CMD, PRED_CMD_IBPB);
}

static inline void spec_ctrl_ibpb(void)
{
	if (ibpb_enabled())
		__spec_ctrl_ibpb();
}

static inline void spec_ctrl_ibpb_if_different_creds(struct task_struct *next)
{
	if (ibpb_enabled() &&
	   (!next || __ptrace_may_access(next, PTRACE_MODE_IBPB))) {
		__spec_ctrl_ibpb();

		if (static_cpu_has(X86_FEATURE_SMEP))
			fill_RSB();
	}
}

static __always_inline void stuff_RSB(void)
{
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

static inline bool is_skylake_era(void)
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

#endif /* __ASSEMBLY__ */
#endif /* _ASM_X86_SPEC_CTRL_H */
