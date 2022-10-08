/* Exports for assembly files.
   All C exports should go in the respective C files. */

#include <linux/module.h>
#include <linux/smp.h>

#include <net/checksum.h>

#include <asm/processor.h>
#include <asm/pgtable.h>
#include <asm/uaccess.h>
#include <asm/desc.h>
#include <asm/ftrace.h>
#include <asm/asm.h>

#ifdef CONFIG_FUNCTION_TRACER
/* mcount and __fentry__ are defined in assembly */
#ifdef CC_USING_FENTRY
EXPORT_SYMBOL(__fentry__);
#else
EXPORT_SYMBOL(mcount);
#endif
#endif

EXPORT_SYMBOL(__get_user_1);
EXPORT_SYMBOL(__get_user_2);
EXPORT_SYMBOL(__get_user_4);
EXPORT_SYMBOL(__get_user_8);
EXPORT_SYMBOL(__put_user_1);
EXPORT_SYMBOL(__put_user_2);
EXPORT_SYMBOL(__put_user_4);
EXPORT_SYMBOL(__put_user_8);

EXPORT_SYMBOL(copy_user_generic_string);
EXPORT_SYMBOL(copy_user_generic_unrolled);
EXPORT_SYMBOL(copy_user_enhanced_fast_string);
EXPORT_SYMBOL(__copy_user_nocache);
EXPORT_SYMBOL(_copy_from_user);
EXPORT_SYMBOL(_copy_to_user);

EXPORT_SYMBOL_GPL(__memcpy_mcsafe);

#ifdef CONFIG_MCSAFE_TEST
extern unsigned long mcsafe_test_src, mcsafe_test_dst;
EXPORT_SYMBOL_GPL(mcsafe_test_src);
EXPORT_SYMBOL_GPL(mcsafe_test_dst);
#endif

EXPORT_SYMBOL(copy_page);
EXPORT_SYMBOL(clear_page);

EXPORT_SYMBOL(csum_partial);

/*
 * Export string functions. We normally rely on gcc builtin for most of these,
 * but gcc sometimes decides not to inline them.
 */
#undef memcpy
#undef memset
#undef memmove

extern void *memset(void *, int, __kernel_size_t);
extern void *memcpy(void *, const void *, __kernel_size_t);
extern void *__memcpy(void *, const void *, __kernel_size_t);

EXPORT_SYMBOL(memset);
EXPORT_SYMBOL(memcpy);
EXPORT_SYMBOL(__memcpy);
EXPORT_SYMBOL(memmove);

#ifndef CONFIG_DEBUG_VIRTUAL
EXPORT_SYMBOL(phys_base);
#endif
EXPORT_SYMBOL(empty_zero_page);
EXPORT_SYMBOL(init_level4_pgt);
#ifndef CONFIG_PARAVIRT
EXPORT_SYMBOL(native_load_gs_index);
#endif

#define EXPORT_THUNK(reg)						\
	extern void __x86_indirect_thunk_ ## reg(void);			\
	EXPORT_SYMBOL(__x86_indirect_thunk_ ## reg)

#ifdef CONFIG_RETPOLINE
EXPORT_THUNK(rax);
EXPORT_THUNK(rbx);
EXPORT_THUNK(rcx);
EXPORT_THUNK(rdx);
EXPORT_THUNK(rsi);
EXPORT_THUNK(rdi);
EXPORT_THUNK(rbp);
EXPORT_THUNK(r8);
EXPORT_THUNK(r9);
EXPORT_THUNK(r10);
EXPORT_THUNK(r11);
EXPORT_THUNK(r12);
EXPORT_THUNK(r13);
EXPORT_THUNK(r14);
EXPORT_THUNK(r15);

extern void __x86_return_thunk(void);
EXPORT_SYMBOL(__x86_return_thunk);

extern void zen_untrain_ret(void);
EXPORT_SYMBOL(zen_untrain_ret);

extern void entry_ibpb(void);
EXPORT_SYMBOL_GPL(entry_ibpb);
#endif
