/*
 * Defines x86 CPU feature bits
 */
#ifndef _ASM_X86_CPUFEATURE_H
#define _ASM_X86_CPUFEATURE_H

#include <asm/processor.h>

#if defined(__KERNEL__) && !defined(__ASSEMBLY__)

#include <asm/asm.h>
#include <linux/bitops.h>

enum cpuid_leafs
{
	CPUID_1_EDX		= 0,
	CPUID_8000_0001_EDX,
	CPUID_8086_0001_EDX,
	CPUID_LNX_1,
	CPUID_1_ECX,
	CPUID_C000_0001_EDX,
	CPUID_8000_0001_ECX,
	CPUID_LNX_2,
	CPUID_LNX_3,
	CPUID_7_0_EBX,
	CPUID_D_1_EAX,
	CPUID_LNX_4,
	CPUID_DUMMY,
	CPUID_8000_0008_EBX,
	CPUID_6_EAX,
	CPUID_8000_000A_EDX,
	CPUID_7_ECX,
	CPUID_8000_0007_EBX,
	CPUID_7_EDX,
};

extern const char * const x86_cap_flags[NCAPINTS*32];
extern const char * const x86_power_flags[32];

#define test_cpu_cap(c, bit)						\
	 test_bit(bit, (unsigned long *)((c)->x86_capability))

#define REQUIRED_MASK_BIT_SET(bit)					\
	 ( (((bit)>>5)==0  && (1UL<<((bit)&31) & REQUIRED_MASK0 )) ||	\
	   (((bit)>>5)==1  && (1UL<<((bit)&31) & REQUIRED_MASK1 )) ||	\
	   (((bit)>>5)==2  && (1UL<<((bit)&31) & REQUIRED_MASK2 )) ||	\
	   (((bit)>>5)==3  && (1UL<<((bit)&31) & REQUIRED_MASK3 )) ||	\
	   (((bit)>>5)==4  && (1UL<<((bit)&31) & REQUIRED_MASK4 )) ||	\
	   (((bit)>>5)==5  && (1UL<<((bit)&31) & REQUIRED_MASK5 )) ||	\
	   (((bit)>>5)==6  && (1UL<<((bit)&31) & REQUIRED_MASK6 )) ||	\
	   (((bit)>>5)==7  && (1UL<<((bit)&31) & REQUIRED_MASK7 )) ||	\
	   (((bit)>>5)==8  && (1UL<<((bit)&31) & REQUIRED_MASK8 )) ||	\
	   (((bit)>>5)==9  && (1UL<<((bit)&31) & REQUIRED_MASK9 )) ||	\
	   (((bit)>>5)==10 && (1UL<<((bit)&31) & REQUIRED_MASK10)) ||	\
	   (((bit)>>5)==11 && (1UL<<((bit)&31) & REQUIRED_MASK11)) ||	\
	   (((bit)>>5)==12 && (1UL<<((bit)&31) & REQUIRED_MASK12)) ||	\
	   (((bit)>>5)==13 && (1UL<<((bit)&31) & REQUIRED_MASK13)) ||	\
	   (((bit)>>5)==14 && (1UL<<((bit)&31) & REQUIRED_MASK14)) ||	\
	   (((bit)>>5)==15 && (1UL<<((bit)&31) & REQUIRED_MASK15)) ||	\
	   (((bit)>>5)==16 && (1UL<<((bit)&31) & REQUIRED_MASK16)) ||   \
	   (((bit)>>5)==17 && (1UL<<((bit)&31) & REQUIRED_MASK17)) ||   \
	   (((bit)>>5)==18 && (1UL<<((bit)&31) & REQUIRED_MASK18)) )

#define DISABLED_MASK_BIT_SET(bit)					\
	 ( (((bit)>>5)==0  && (1UL<<((bit)&31) & DISABLED_MASK0 )) ||	\
	   (((bit)>>5)==1  && (1UL<<((bit)&31) & DISABLED_MASK1 )) ||	\
	   (((bit)>>5)==2  && (1UL<<((bit)&31) & DISABLED_MASK2 )) ||	\
	   (((bit)>>5)==3  && (1UL<<((bit)&31) & DISABLED_MASK3 )) ||	\
	   (((bit)>>5)==4  && (1UL<<((bit)&31) & DISABLED_MASK4 )) ||	\
	   (((bit)>>5)==5  && (1UL<<((bit)&31) & DISABLED_MASK5 )) ||	\
	   (((bit)>>5)==6  && (1UL<<((bit)&31) & DISABLED_MASK6 )) ||	\
	   (((bit)>>5)==7  && (1UL<<((bit)&31) & DISABLED_MASK7 )) ||	\
	   (((bit)>>5)==8  && (1UL<<((bit)&31) & DISABLED_MASK8 )) ||	\
	   (((bit)>>5)==9  && (1UL<<((bit)&31) & DISABLED_MASK9 )) ||	\
	   (((bit)>>5)==10 && (1UL<<((bit)&31) & DISABLED_MASK10)) ||	\
	   (((bit)>>5)==11 && (1UL<<((bit)&31) & DISABLED_MASK11)) ||	\
	   (((bit)>>5)==12 && (1UL<<((bit)&31) & DISABLED_MASK12)) ||	\
	   (((bit)>>5)==13 && (1UL<<((bit)&31) & DISABLED_MASK13)) ||	\
	   (((bit)>>5)==14 && (1UL<<((bit)&31) & DISABLED_MASK14)) ||	\
	   (((bit)>>5)==15 && (1UL<<((bit)&31) & DISABLED_MASK15)) ||	\
	   (((bit)>>5)==16 && (1UL<<((bit)&31) & DISABLED_MASK16)) ||   \
	   (((bit)>>5)==17 && (1UL<<((bit)&31) & DISABLED_MASK17)) ||   \
	   (((bit)>>5)==18 && (1UL<<((bit)&31) & DISABLED_MASK18)) )

#define cpu_has(c, bit)							\
	(__builtin_constant_p(bit) && REQUIRED_MASK_BIT_SET(bit) ? 1 :	\
	 test_cpu_cap(c, bit))

#define this_cpu_has(bit)						\
	(__builtin_constant_p(bit) && REQUIRED_MASK_BIT_SET(bit) ? 1 : 	\
	 x86_this_cpu_test_bit(bit, (unsigned long *)&cpu_info.x86_capability))

/*
 * This macro is for detection of features which need kernel
 * infrastructure to be used.  It may *not* directly test the CPU
 * itself.  Use the cpu_has() family if you want true runtime
 * testing of CPU features, like in hypervisor code where you are
 * supporting a possible guest feature where host support for it
 * is not relevant.
 */
#define cpu_feature_enabled(bit)	\
	(__builtin_constant_p(bit) && DISABLED_MASK_BIT_SET(bit) ? 0 :	\
	 cpu_has(&boot_cpu_data, bit))

#define boot_cpu_has(bit)	cpu_has(&boot_cpu_data, bit)

#define set_cpu_cap(c, bit)	set_bit(bit, (unsigned long *)((c)->x86_capability))

extern void setup_clear_cpu_cap(unsigned int bit);
extern void clear_cpu_cap(struct cpuinfo_x86 *c, unsigned int bit);

#define setup_force_cpu_cap(bit) do { \
	set_cpu_cap(&boot_cpu_data, bit);	\
	set_bit(bit, (unsigned long *)cpu_caps_set);	\
} while (0)

#define setup_force_cpu_bug(bit) setup_force_cpu_cap(bit)

#define cpu_has_fpu		boot_cpu_has(X86_FEATURE_FPU)
#define cpu_has_de		boot_cpu_has(X86_FEATURE_DE)
#define cpu_has_pse		boot_cpu_has(X86_FEATURE_PSE)
#define cpu_has_tsc		boot_cpu_has(X86_FEATURE_TSC)
#define cpu_has_pge		boot_cpu_has(X86_FEATURE_PGE)
#define cpu_has_apic		boot_cpu_has(X86_FEATURE_APIC)
#define cpu_has_sep		boot_cpu_has(X86_FEATURE_SEP)
#define cpu_has_mtrr		boot_cpu_has(X86_FEATURE_MTRR)
#define cpu_has_mmx		boot_cpu_has(X86_FEATURE_MMX)
#define cpu_has_fxsr		boot_cpu_has(X86_FEATURE_FXSR)
#define cpu_has_xmm		boot_cpu_has(X86_FEATURE_XMM)
#define cpu_has_xmm2		boot_cpu_has(X86_FEATURE_XMM2)
#define cpu_has_xmm3		boot_cpu_has(X86_FEATURE_XMM3)
#define cpu_has_ssse3		boot_cpu_has(X86_FEATURE_SSSE3)
#define cpu_has_aes		boot_cpu_has(X86_FEATURE_AES)
#define cpu_has_avx		boot_cpu_has(X86_FEATURE_AVX)
#define cpu_has_avx2		boot_cpu_has(X86_FEATURE_AVX2)
#define cpu_has_ht		boot_cpu_has(X86_FEATURE_HT)
#define cpu_has_nx		boot_cpu_has(X86_FEATURE_NX)
#define cpu_has_xstore		boot_cpu_has(X86_FEATURE_XSTORE)
#define cpu_has_xstore_enabled	boot_cpu_has(X86_FEATURE_XSTORE_EN)
#define cpu_has_xcrypt		boot_cpu_has(X86_FEATURE_XCRYPT)
#define cpu_has_xcrypt_enabled	boot_cpu_has(X86_FEATURE_XCRYPT_EN)
#define cpu_has_ace2		boot_cpu_has(X86_FEATURE_ACE2)
#define cpu_has_ace2_enabled	boot_cpu_has(X86_FEATURE_ACE2_EN)
#define cpu_has_phe		boot_cpu_has(X86_FEATURE_PHE)
#define cpu_has_phe_enabled	boot_cpu_has(X86_FEATURE_PHE_EN)
#define cpu_has_pmm		boot_cpu_has(X86_FEATURE_PMM)
#define cpu_has_pmm_enabled	boot_cpu_has(X86_FEATURE_PMM_EN)
#define cpu_has_ds		boot_cpu_has(X86_FEATURE_DS)
#define cpu_has_pebs		boot_cpu_has(X86_FEATURE_PEBS)
#define cpu_has_clflush		boot_cpu_has(X86_FEATURE_CLFLUSH)
#define cpu_has_bts		boot_cpu_has(X86_FEATURE_BTS)
#define cpu_has_gbpages		boot_cpu_has(X86_FEATURE_GBPAGES)
#define cpu_has_arch_perfmon	boot_cpu_has(X86_FEATURE_ARCH_PERFMON)
#define cpu_has_pat		boot_cpu_has(X86_FEATURE_PAT)
#define cpu_has_xmm4_1		boot_cpu_has(X86_FEATURE_XMM4_1)
#define cpu_has_xmm4_2		boot_cpu_has(X86_FEATURE_XMM4_2)
#define cpu_has_x2apic		boot_cpu_has(X86_FEATURE_X2APIC)
#define cpu_has_xsave		boot_cpu_has(X86_FEATURE_XSAVE)
#define cpu_has_xsaveopt	boot_cpu_has(X86_FEATURE_XSAVEOPT)
#define cpu_has_xsaves          boot_cpu_has(X86_FEATURE_XSAVES)
#define cpu_has_osxsave		boot_cpu_has(X86_FEATURE_OSXSAVE)
#define cpu_has_hypervisor	boot_cpu_has(X86_FEATURE_HYPERVISOR)
#define cpu_has_pclmulqdq	boot_cpu_has(X86_FEATURE_PCLMULQDQ)
#define cpu_has_perfctr_core	boot_cpu_has(X86_FEATURE_PERFCTR_CORE)
#define cpu_has_perfctr_nb	boot_cpu_has(X86_FEATURE_PERFCTR_NB)
#define cpu_has_perfctr_l2	boot_cpu_has(X86_FEATURE_PERFCTR_L2)
#define cpu_has_cx8		boot_cpu_has(X86_FEATURE_CX8)
#define cpu_has_cx16		boot_cpu_has(X86_FEATURE_CX16)
#define cpu_has_eager_fpu	boot_cpu_has(X86_FEATURE_EAGER_FPU)
#define cpu_has_topoext		boot_cpu_has(X86_FEATURE_TOPOEXT)
#define cpu_has_bpext		boot_cpu_has(X86_FEATURE_BPEXT)

#if __GNUC__ >= 4
/*
 * Static testing of CPU features.  Used the same as boot_cpu_has().
 * These are only valid after alternatives have run, but will statically
 * patch the target code for additional performance.
 *
 */
static __always_inline __pure bool __static_cpu_has(u16 bit)
{
#if __GNUC__ > 4 || __GNUC_MINOR__ >= 5
		asm_volatile_goto("1: jmp %l[t_no]\n"
			 "2:\n"
			 ".section .altinstructions,\"a\"\n"
			 " .long 1b - .\n"
			 " .long 0\n"		/* no replacement */
			 " .word %P0\n"		/* feature bit */
			 " .byte 2b - 1b\n"	/* source len */
			 " .byte 0\n"		/* replacement len */
			 ".previous\n"
			 /* skipping size check since replacement size = 0 */
			 : : "i" (bit) : : t_no);
		return true;
	t_no:
		return false;
#else
		u8 flag;
		/* Open-coded due to __stringify() in ALTERNATIVE() */
		asm volatile("1: movb $0,%0\n"
			     "2:\n"
			     ".section .altinstructions,\"a\"\n"
			     " .long 1b - .\n"
			     " .long 3f - .\n"
			     " .word %P1\n"		/* feature bit */
			     " .byte 2b - 1b\n"		/* source len */
			     " .byte 4f - 3f\n"		/* replacement len */
			     ".previous\n"
			     ".section .discard,\"aw\",@progbits\n"
			     " .byte 0xff + (4f-3f) - (2b-1b)\n" /* size check */
			     ".previous\n"
			     ".section .altinstr_replacement,\"ax\"\n"
			     "3: movb $1,%0\n"
			     "4:\n"
			     ".previous\n"
			     : "=qm" (flag) : "i" (bit));
		return flag;
#endif
}

#define static_cpu_has(bit)					\
(								\
	__builtin_constant_p(boot_cpu_has(bit)) ?		\
		boot_cpu_has(bit) :				\
	__builtin_constant_p(bit) ?				\
		__static_cpu_has(bit) :				\
		boot_cpu_has(bit)				\
)
#else
/*
 * gcc 3.x is too stupid to do the static test; fall back to dynamic.
 */
#define static_cpu_has(bit) boot_cpu_has(bit)
#endif

#define cpu_has_bug(c, bit)	cpu_has(c, (bit))
#define set_cpu_bug(c, bit)	set_cpu_cap(c, (bit))
#define clear_cpu_bug(c, bit)	clear_cpu_cap(c, (bit));

#define static_cpu_has_bug(bit)	static_cpu_has((bit))
#define boot_cpu_has_bug(bit)	cpu_has_bug(&boot_cpu_data, (bit))

#endif /* defined(__KERNEL__) && !defined(__ASSEMBLY__) */

#endif /* _ASM_X86_CPUFEATURE_H */
