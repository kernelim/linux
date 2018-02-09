#include <linux/module.h>

#include <asm/checksum.h>
#include <asm/pgtable.h>
#include <asm/desc.h>
#include <asm/ftrace.h>
#include <asm/asm.h>

#ifdef CONFIG_FUNCTION_TRACER
/* mcount is defined in assembly */
EXPORT_SYMBOL(mcount);
#endif

/*
 * Note, this is a prototype to get at the symbol for
 * the export, but dont use it from C code, it is used
 * by assembly code and is not using C calling convention!
 */
#ifndef CONFIG_X86_CMPXCHG64
extern void cmpxchg8b_emu(void);
EXPORT_SYMBOL(cmpxchg8b_emu);
#endif

/* Networking helper routines. */
EXPORT_SYMBOL(csum_partial_copy_generic);

EXPORT_SYMBOL(__get_user_1);
EXPORT_SYMBOL(__get_user_2);
EXPORT_SYMBOL(__get_user_4);

EXPORT_SYMBOL(__put_user_1);
EXPORT_SYMBOL(__put_user_2);
EXPORT_SYMBOL(__put_user_4);
EXPORT_SYMBOL(__put_user_8);

EXPORT_SYMBOL(strstr);

EXPORT_SYMBOL(csum_partial);
EXPORT_SYMBOL(empty_zero_page);

#ifdef CONFIG_RETPOLINE
#define EXPORT_THUNK(reg)						\
	extern void __x86_indirect_thunk_ ## reg(void);			\
	EXPORT_SYMBOL(__x86_indirect_thunk_ ## reg)

EXPORT_THUNK(eax);
EXPORT_THUNK(ebx);
EXPORT_THUNK(ecx);
EXPORT_THUNK(edx);
EXPORT_THUNK(esi);
EXPORT_THUNK(edi);
EXPORT_THUNK(ebp);
#endif /* CONFIG_RETPOLINE */
