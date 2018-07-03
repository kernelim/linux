/*
 * Copyright (C) 1994 Linus Torvalds
 *
 * Pentium III FXSR, SSE support
 * General FPU state handling cleanups
 *	Gareth Hughes <gareth@valinux.com>, May 2000
 * x86-64 work by Andi Kleen 2002
 */

#ifndef _FPU_INTERNAL_H
#define _FPU_INTERNAL_H

#include <linux/kernel_stat.h>
#include <linux/regset.h>
#include <linux/compat.h>
#include <linux/slab.h>
#include <asm/asm.h>
#include <asm/cpufeature.h>
#include <asm/processor.h>
#include <asm/sigcontext.h>
#include <asm/user.h>
#include <asm/uaccess.h>
#include <asm/xsave.h>

#ifdef CONFIG_X86_64
# include <asm/sigcontext32.h>
# include <asm/user32.h>
int ia32_setup_rt_frame(int sig, struct k_sigaction *ka, siginfo_t *info,
			compat_sigset_t *set, struct pt_regs *regs);
int ia32_setup_frame(int sig, struct k_sigaction *ka,
		     compat_sigset_t *set, struct pt_regs *regs);
#else
# define user_i387_ia32_struct	user_i387_struct
# define user32_fxsr_struct	user_fxsr_struct
# define ia32_setup_frame	__setup_frame
# define ia32_setup_rt_frame	__setup_rt_frame
#endif

extern unsigned int mxcsr_feature_mask;
extern void fpu_init(void);
extern void eager_fpu_init(void);

extern void convert_from_fxsr(struct user_i387_ia32_struct *env,
			      struct task_struct *tsk);
extern void convert_to_fxsr(struct task_struct *tsk,
			    const struct user_i387_ia32_struct *env);

extern user_regset_active_fn fpregs_active, xfpregs_active;
extern user_regset_get_fn fpregs_get, xfpregs_get, fpregs_soft_get,
				xstateregs_get;
extern user_regset_set_fn fpregs_set, xfpregs_set, fpregs_soft_set,
				 xstateregs_set;

/*
 * xstateregs_active == fpregs_active. Please refer to the comment
 * at the definition of fpregs_active.
 */
#define xstateregs_active	fpregs_active

#ifdef CONFIG_MATH_EMULATION
# define HAVE_HWFP		(boot_cpu_data.hard_math)
extern void finit_soft_fpu(struct i387_soft_struct *soft);
#else
# define HAVE_HWFP		1
static inline void finit_soft_fpu(struct i387_soft_struct *soft) {}
#endif

static inline int is_ia32_compat_frame(void)
{
	return config_enabled(CONFIG_IA32_EMULATION) &&
	       test_thread_flag(TIF_IA32);
}

static inline int is_ia32_frame(void)
{
	return config_enabled(CONFIG_X86_32) || is_ia32_compat_frame();
}

#define X87_FSW_ES (1 << 7)	/* Exception Summary */

static __always_inline __pure bool use_eager_fpu(void)
{
	return static_cpu_has(X86_FEATURE_EAGER_FPU);
}

static __always_inline __pure bool use_xsaveopt(void)
{
	return static_cpu_has(X86_FEATURE_XSAVEOPT);
}

static __always_inline __pure bool use_xsave(void)
{
	return static_cpu_has(X86_FEATURE_XSAVE);
}

static __always_inline __pure bool use_fxsr(void)
{
        return static_cpu_has(X86_FEATURE_FXSR);
}

static inline void fx_finit(struct i387_fxsave_struct *fx)
{
	fx->cwd = 0x37f;
	if (cpu_has_xmm)
		fx->mxcsr = MXCSR_DEFAULT;
}

extern void __sanitize_i387_state(struct task_struct *);

static inline void sanitize_i387_state(struct task_struct *tsk)
{
	if (!use_xsaveopt())
		return;
	__sanitize_i387_state(tsk);
}

#define check_insn(insn, output, input...)				\
({									\
	int err;							\
	asm volatile("1:" #insn "\n\t"					\
		     "2:\n"						\
		     ".section .fixup,\"ax\"\n"				\
		     "3:  movl $-1,%[err]\n"				\
		     "    jmp  2b\n"					\
		     ".previous\n"					\
		     _ASM_EXTABLE(1b, 3b)				\
		     : [err] "=r" (err), output				\
		     : "0"(0), input);					\
	err;								\
})

static inline int fsave_user(struct i387_fsave_struct __user *fx)
{
	return check_insn(fnsave %[fx]; fwait,  [fx] "=m" (*fx), "m" (*fx));
}

static inline int fxsave_user(struct i387_fxsave_struct __user *fx)
{
	if (config_enabled(CONFIG_X86_32))
		return check_insn(fxsave %[fx], [fx] "=m" (*fx), "m" (*fx));

	/* See comment in fpu_fxsave() below. */
	return check_insn(rex64/fxsave (%[fx]), "=m" (*fx), [fx] "R" (fx));
}

static inline int fxrstor_checking(struct i387_fxsave_struct *fx)
{
	if (config_enabled(CONFIG_X86_32))
		return check_insn(fxrstor %[fx], "=m" (*fx), [fx] "m" (*fx));

	/* See comment in fpu_fxsave() below. */
	return check_insn(rex64/fxrstor (%[fx]), "=m" (*fx), [fx] "R" (fx),
			  "m" (*fx));
}

static inline int frstor_checking(struct i387_fsave_struct *fx)
{
	return check_insn(frstor %[fx], "=m" (*fx), [fx] "m" (*fx));
}

static inline void fpu_fxsave(struct fpu *fpu)
{
	if (config_enabled(CONFIG_X86_32))
		asm volatile( "fxsave %[fx]" : [fx] "=m" (fpu->state->fxsave));
	else {
		/* Using "rex64; fxsave %0" is broken because, if the memory
		 * operand uses any extended registers for addressing, a second
		 * REX prefix will be generated (to the assembler, rex64
		 * followed by semicolon is a separate instruction), and hence
		 * the 64-bitness is lost.
		 *
		 * Using "fxsaveq %0" would be the ideal choice, but is only
		 * supported starting with gas 2.16.
		 *
		 * Using, as a workaround, the properly prefixed form below
		 * isn't accepted by any binutils version so far released,
		 * complaining that the same type of prefix is used twice if
		 * an extended register is needed for addressing (fix submitted
		 * to mainline 2005-11-21).
		 *
		 *  asm volatile("rex64/fxsave %0" : "=m" (fpu->state->fxsave));
		 *
		 * This, however, we can work around by forcing the compiler to
		 * select an addressing mode that doesn't require extended
		 * registers.
		 */
		asm volatile( "rex64/fxsave (%[fx])"
			     : "=m" (fpu->state->fxsave)
			     : [fx] "R" (&fpu->state->fxsave));
	}
}

/*
 * These must be called with preempt disabled. Returns
 * 'true' if the FPU state is still intact.
 */
static inline int fpu_save_init(struct fpu *fpu)
{
	if (use_xsave()) {
		fpu_xsave(fpu);

		/*
		 * xsave header may indicate the init state of the FP.
		 */
		if (!(fpu->state->xsave.xsave_hdr.xstate_bv & XSTATE_FP))
			return 1;
	} else if (use_fxsr()) {
		fpu_fxsave(fpu);
	} else {
		asm volatile("fnsave %[fx]; fwait"
			     : [fx] "=m" (fpu->state->fsave));
		return 0;
	}

	/*
	 * If exceptions are pending, we need to clear them so
	 * that we don't randomly get exceptions later.
	 *
	 * FIXME! Is this perhaps only true for the old-style
	 * irq13 case? Maybe we could leave the x87 state
	 * intact otherwise?
	 */
	if (unlikely(fpu->state->fxsave.swd & X87_FSW_ES)) {
		asm volatile("fnclex");
		return 0;
	}
	return 1;
}

static inline int __save_init_fpu(struct task_struct *tsk)
{
	return fpu_save_init((struct fpu *)&tsk->thread.xstate);
}

static inline int fpu_restore_checking(struct fpu *fpu)
{
	if (use_xsave())
		return fpu_xrstor_checking(&fpu->state->xsave);
	else if (use_fxsr())
		return fxrstor_checking(&fpu->state->fxsave);
	else
		return frstor_checking(&fpu->state->fsave);
}

static inline int restore_fpu_checking(struct task_struct *tsk)
{
	/* AMD K7/K8 CPUs don't save/restore FDP/FIP/FOP unless an exception
	   is pending.  Clear the x87 state here by setting it to fixed
	   values. "m" is a random variable that should be in L1 */
	alternative_input(
		_ASM_MK_NOP(GENERIC_NOP8)
		_ASM_MK_NOP(GENERIC_NOP2),
		"emms\n\t"		/* clear stack tags */
		"fildl %P[addr]",	/* set F?P to defined value */
		X86_FEATURE_FXSAVE_LEAK,
		[addr] "m" (tsk->has_fpu));

	return fpu_restore_checking((struct fpu *)&tsk->thread.xstate);
}

/*
 * Software FPU state helpers. Careful: these need to
 * be preemption protection *and* they need to be
 * properly paired with the CR0.TS changes!
 */
static inline int __thread_has_fpu(struct task_struct *tsk)
{
	return tsk->has_fpu;
}

/* Must be paired with an 'stts' after! */
static inline void __thread_clear_has_fpu(struct task_struct *tsk)
{
	tsk->has_fpu = 0;
}

/* Must be paired with a 'clts' before! */
static inline void __thread_set_has_fpu(struct task_struct *tsk)
{
	tsk->has_fpu = 1;
}

/*
 * Encapsulate the CR0.TS handling together with the
 * software flag.
 *
 * These generally need preemption protection to work,
 * do try to avoid using these on their own.
 */
static inline void __thread_fpu_end(struct task_struct *tsk)
{
	__thread_clear_has_fpu(tsk);
	if (!use_eager_fpu())
		stts();
}

static inline void __thread_fpu_begin(struct task_struct *tsk)
{
	if (!use_eager_fpu())
		clts();
	__thread_set_has_fpu(tsk);
}

static inline void drop_fpu(struct task_struct *tsk)
{
	/*
	 * Forget coprocessor state..
	 */
	preempt_disable();
	tsk->fpu_counter = 0;

	if (__thread_has_fpu(tsk)) {
		/* Ignore delayed exceptions from user space */
		asm volatile("1: fwait\n"
			     "2:\n"
			     _ASM_EXTABLE(1b, 2b));
		__thread_fpu_end(tsk);
	}

	clear_stopped_child_used_math(tsk);
	preempt_enable();
}

static inline void restore_init_xstate(void)
{
	if (use_xsave())
		xrstor_state(init_xstate_buf, -1);
	else
		fxrstor_checking(&init_xstate_buf->i387);
}

/*
 * Reset the FPU state in the eager case and drop it in the lazy case (later use
 * will reinit it).
 */
static inline void fpu_reset_state(struct task_struct *tsk)
{
	if (!use_eager_fpu())
		drop_fpu(tsk);
	else
		restore_init_xstate();
}

/*
 * FPU state switching for scheduling.
 *
 * This is a two-stage process:
 *
 *  - switch_fpu_prepare() saves the old state and
 *    sets the new state of the CR0.TS bit. This is
 *    done within the context of the old process.
 *
 *  - switch_fpu_finish() restores the new state as
 *    necessary.
 */
typedef struct { int preload; } fpu_switch_t;

/*
 * FIXME! We could do a totally lazy restore, but we need to
 * add a per-cpu "this was the task that last touched the FPU
 * on this CPU" variable, and the task needs to have a "I last
 * touched the FPU on this CPU" and check them.
 *
 * We don't do that yet, so "fpu_lazy_restore()" always returns
 * false, but some day..
 */
static inline int fpu_lazy_restore(struct task_struct *new, unsigned int cpu)
{
	return 0;
}

static inline fpu_switch_t switch_fpu_prepare(struct task_struct *old, struct task_struct *new, int cpu)
{
	fpu_switch_t fpu;

	/*
	 * If the task has used the math, pre-load the FPU on xsave processors
	 * or if the past 5 consecutive context-switches used math.
	 */
	fpu.preload = tsk_used_math(new) && (use_eager_fpu() ||
					     new->fpu_counter > 5);
	if (__thread_has_fpu(old)) {
		if (!__save_init_fpu(old))
			cpu = ~0;
		old->has_fpu = 0;

		/* Don't change CR0.TS if we just switch! */
		if (fpu.preload) {
			new->fpu_counter++;
			__thread_set_has_fpu(new);
			prefetch(new->thread.xstate);
		} else if (!use_eager_fpu())
			stts();
	} else {
		old->fpu_counter = 0;
		if (fpu.preload) {
			new->fpu_counter++;
			if (!use_eager_fpu() && fpu_lazy_restore(new, cpu))
				fpu.preload = 0;
			else
				prefetch(new->thread.xstate);
			__thread_fpu_begin(new);
		}
	}
	return fpu;
}

/*
 * By the time this gets called, we've already cleared CR0.TS and
 * given the process the FPU if we are going to preload the FPU
 * state - all we need to do is to conditionally restore the register
 * state itself.
 */
static inline void switch_fpu_finish(struct task_struct *new, fpu_switch_t fpu)
{
	if (fpu.preload) {
		if (unlikely(restore_fpu_checking(new)))
			fpu_reset_state(new);
	}
}

/*
 * Signal frame handlers...
 */
extern int save_xstate_sig(void __user *buf, void __user *fx, int size);
extern int __restore_xstate_sig(void __user *buf, void __user *fx, int size);

static inline int xstate_sigframe_size(void)
{
	return use_xsave() ? xstate_size + FP_XSTATE_MAGIC2_SIZE : xstate_size;
}

static inline int restore_xstate_sig(void __user *buf, int ia32_frame)
{
	void __user *buf_fx = buf;
	int size = xstate_sigframe_size();

	if (ia32_frame && use_fxsr()) {
		buf_fx = buf + sizeof(struct i387_fsave_struct);
		size += sizeof(struct i387_fsave_struct);
	}

	return __restore_xstate_sig(buf, buf_fx, size);
}

/*
 * Needs to be preemption-safe.
 *
 * NOTE! user_fpu_begin() must be used only immediately before restoring
 * the save state. It does not do any saving/restoring on its own. In
 * lazy FPU mode, it is just an optimization to avoid a #NM exception,
 * the task can lose the FPU right after preempt_enable().
 */
static inline void user_fpu_begin(void)
{
	preempt_disable();
	if (!user_has_fpu())
		__thread_fpu_begin(current);
	preempt_enable();
}

static inline void __save_fpu(struct task_struct *tsk)
{
	if (use_xsave())
		xsave_state(&tsk->thread.xstate->xsave, -1);
	else
		fpu_fxsave((struct fpu *)&tsk->thread.xstate);
}

/*
 * i387 state interaction
 */
static inline unsigned short get_fpu_cwd(struct task_struct *tsk)
{
	if (cpu_has_fxsr) {
		return tsk->thread.xstate->fxsave.cwd;
	} else {
		return (unsigned short)tsk->thread.xstate->fsave.cwd;
	}
}

static inline unsigned short get_fpu_swd(struct task_struct *tsk)
{
	if (cpu_has_fxsr) {
		return tsk->thread.xstate->fxsave.swd;
	} else {
		return (unsigned short)tsk->thread.xstate->fsave.swd;
	}
}

static inline unsigned short get_fpu_mxcsr(struct task_struct *tsk)
{
	if (cpu_has_xmm) {
		return tsk->thread.xstate->fxsave.mxcsr;
	} else {
		return MXCSR_DEFAULT;
	}
}

static bool fpu_allocated(struct fpu *fpu)
{
	return fpu->state != NULL;
}

static inline int fpu_alloc(struct fpu *fpu)
{
	if (fpu_allocated(fpu))
		return 0;
	fpu->state = kmem_cache_alloc(task_xstate_cachep, GFP_KERNEL);
	if (!fpu->state)
		return -ENOMEM;
	WARN_ON((unsigned long)fpu->state & 15);
	return 0;
}

static inline void fpu_free(struct fpu *fpu)
{
	if (fpu->state) {
		kmem_cache_free(task_xstate_cachep, fpu->state);
		fpu->state = NULL;
	}
}

static inline void fpu_copy(struct task_struct *dst, struct task_struct *src)
{
	if (use_eager_fpu()) {
		memset(dst->thread.xstate, 0, xstate_size);
		__save_fpu(dst);
	} else {
		unlazy_fpu(src);
		memcpy(dst->thread.xstate, src->thread.xstate, xstate_size);
	}
}

static inline unsigned long
alloc_mathframe(unsigned long sp, int ia32_frame, unsigned long *buf_fx,
		unsigned long *size)
{
	unsigned long frame_size = xstate_sigframe_size();

	*buf_fx = sp = round_down(sp - frame_size, 64);
	if (ia32_frame && use_fxsr()) {
		frame_size += sizeof(struct i387_fsave_struct);
		sp -= sizeof(struct i387_fsave_struct);
	}

	*size = frame_size;
	return sp;
}

#endif
