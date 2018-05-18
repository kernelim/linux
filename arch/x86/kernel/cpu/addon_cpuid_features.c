/*
 *	Routines to indentify additional cpu features that are scattered in
 *	cpuid space.
 */
#include <linux/cpu.h>

#include <asm/pat.h>
#include <asm/processor.h>

#include <asm/apic.h>

struct cpuid_bit {
	u16 feature;
	u8 reg;
	u8 bit;
	u32 level;
	u32 sub_leaf;
};

/* Please keep the leaf sorted by cpuid_bit.level for faster search. */
static const struct cpuid_bit cpuid_bits[] = {
	{ X86_FEATURE_DTHERM,		CPUID_EAX, 0, 0x00000006, 0 },
	{ X86_FEATURE_IDA,		CPUID_EAX, 1, 0x00000006, 0 },
	{ X86_FEATURE_ARAT,		CPUID_EAX, 2, 0x00000006, 0 },
	{ X86_FEATURE_PLN,		CPUID_EAX, 4, 0x00000006, 0 },
	{ X86_FEATURE_PTS,		CPUID_EAX, 6, 0x00000006, 0 },
	{ X86_FEATURE_HWP,		CPUID_EAX, 7, 0x00000006, 0 },
	{ X86_FEATURE_HWP_NOITFY,	CPUID_EAX, 8, 0x00000006, 0 },
	{ X86_FEATURE_HWP_ACT_WINDOW,	CPUID_EAX, 9, 0x00000006, 0 },
	{ X86_FEATURE_HWP_EPP,		CPUID_EAX,10, 0x00000006, 0 },
	{ X86_FEATURE_HWP_PKG_REQ,	CPUID_EAX,11, 0x00000006, 0 },
	{ X86_FEATURE_APERFMPERF,	CPUID_ECX, 0, 0x00000006, 0 },
	{ X86_FEATURE_EPB,		CPUID_ECX, 3, 0x00000006, 0 },
	{ X86_FEATURE_XSAVEOPT,		CPUID_EAX, 0, 0x0000000d, 1 },
	{ X86_FEATURE_CPB,		CPUID_EDX, 9, 0x80000007, 0 },
	{ X86_FEATURE_NPT,		CPUID_EDX, 0, 0x8000000a, 0 },
	{ X86_FEATURE_LBRV,		CPUID_EDX, 1, 0x8000000a, 0 },
	{ X86_FEATURE_SVML,		CPUID_EDX, 2, 0x8000000a, 0 },
	{ X86_FEATURE_NRIPS,		CPUID_EDX, 3, 0x8000000a, 0 },
	{ X86_FEATURE_TSCRATEMSR,	CPUID_EDX, 4, 0x8000000a, 0 },
	{ X86_FEATURE_VMCBCLEAN,	CPUID_EDX, 5, 0x8000000a, 0 },
	{ X86_FEATURE_FLUSHBYASID,	CPUID_EDX, 6, 0x8000000a, 0 },
	{ X86_FEATURE_DECODEASSISTS,	CPUID_EDX, 7, 0x8000000a, 0 },
	{ X86_FEATURE_PAUSEFILTER,	CPUID_EDX,10, 0x8000000a, 0 },
	{ X86_FEATURE_PFTHRESHOLD,	CPUID_EDX,12, 0x8000000a, 0 },
	{ 0, 0, 0, 0, 0 }
};

void init_scattered_cpuid_features(struct cpuinfo_x86 *c)
{
	u32 max_level;
	u32 regs[4];
	const struct cpuid_bit *cb;

	for (cb = cpuid_bits; cb->feature; cb++) {

		/* Verify that the level is valid */
		max_level = cpuid_eax(cb->level & 0xffff0000);
		if (max_level < cb->level ||
		    max_level > (cb->level | 0xffff))
			continue;

		cpuid_count(cb->level, cb->sub_leaf, &regs[CPUID_EAX],
			    &regs[CPUID_EBX], &regs[CPUID_ECX],
			    &regs[CPUID_EDX]);

		if (regs[cb->reg] & (1 << cb->bit))
			set_cpu_cap(c, cb->feature);
	}

	/*
	 * common AMD/Intel features
	 */
	if (c->cpuid_level >= 6) {
		if (cpuid_ecx(6) & 0x1)
			set_cpu_cap(c, X86_FEATURE_APERFMPERF);
	}
}

u32 get_scattered_cpuid_leaf(unsigned int level, unsigned int sub_leaf,
			     enum cpuid_regs_idx reg)
{
	const struct cpuid_bit *cb;
	u32 cpuid_val = 0;

	for (cb = cpuid_bits; cb->feature; cb++) {

		if (level > cb->level)
			continue;

		if (level < cb->level)
			break;

		if (reg == cb->reg && sub_leaf == cb->sub_leaf) {
			if (cpu_has(&boot_cpu_data, cb->feature))
				cpuid_val |= BIT(cb->bit);
		}
	}

	return cpuid_val;
}

EXPORT_SYMBOL_GPL(get_scattered_cpuid_leaf);

/* leaf 0xb SMT level */
#define SMT_LEVEL	0

/* leaf 0xb sub-leaf types */
#define INVALID_TYPE	0
#define SMT_TYPE	1
#define CORE_TYPE	2

#define LEAFB_SUBTYPE(ecx)		(((ecx) >> 8) & 0xff)
#define BITS_SHIFT_NEXT_LEVEL(eax)	((eax) & 0x1f)
#define LEVEL_MAX_SIBLINGS(ebx)		((ebx) & 0xffff)

/*
 * Check for extended topology enumeration cpuid leaf 0xb and if it
 * exists, use it for populating initial_apicid and cpu topology
 * detection.
 */
void __cpuinit detect_extended_topology(struct cpuinfo_x86 *c)
{
#ifdef CONFIG_SMP
	unsigned int eax, ebx, ecx, edx, sub_index;
	unsigned int ht_mask_width, core_plus_mask_width;
	unsigned int core_select_mask, core_level_siblings;
	static bool printed;

	if (c->cpuid_level < 0xb)
		return;

	cpuid_count(0xb, SMT_LEVEL, &eax, &ebx, &ecx, &edx);

	/*
	 * check if the cpuid leaf 0xb is actually implemented.
	 */
	if (ebx == 0 || (LEAFB_SUBTYPE(ecx) != SMT_TYPE))
		return;

	set_cpu_cap(c, X86_FEATURE_XTOPOLOGY);

	/*
	 * initial apic id, which also represents 32-bit extended x2apic id.
	 */
	c->initial_apicid = edx;

	/*
	 * Populate HT related information from sub-leaf level 0.
	 */
	core_level_siblings = smp_num_siblings = LEVEL_MAX_SIBLINGS(ebx);
	core_plus_mask_width = ht_mask_width = BITS_SHIFT_NEXT_LEVEL(eax);

	sub_index = 1;
	do {
		cpuid_count(0xb, sub_index, &eax, &ebx, &ecx, &edx);

		/*
		 * Check for the Core type in the implemented sub leaves.
		 */
		if (LEAFB_SUBTYPE(ecx) == CORE_TYPE) {
			core_level_siblings = LEVEL_MAX_SIBLINGS(ebx);
			core_plus_mask_width = BITS_SHIFT_NEXT_LEVEL(eax);
			break;
		}

		sub_index++;
	} while (LEAFB_SUBTYPE(ecx) != INVALID_TYPE);

	core_select_mask = (~(-1 << core_plus_mask_width)) >> ht_mask_width;

	c->cpu_core_id = apic->phys_pkg_id(c->initial_apicid, ht_mask_width)
						 & core_select_mask;
	c->phys_proc_id = apic->phys_pkg_id(c->initial_apicid, core_plus_mask_width);
	/*
	 * Reinit the apicid, now that we have extended initial_apicid.
	 */
	c->apicid = apic->phys_pkg_id(c->initial_apicid, 0);

	c->x86_max_cores = (core_level_siblings / smp_num_siblings);

	if (!printed) {
		printk(KERN_INFO  "CPU: Physical Processor ID: %d\n",
		       c->phys_proc_id);
		if (c->x86_max_cores > 1)
			printk(KERN_INFO  "CPU: Processor Core ID: %d\n",
			       c->cpu_core_id);
		printed = 1;
	}
	return;
#endif
}
