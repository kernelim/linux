#define pr_fmt(fmt) "SMP alternatives: " fmt

#include <linux/module.h>
#include <linux/sched.h>
#include <linux/perf_event.h>
#include <linux/mutex.h>
#include <linux/list.h>
#include <linux/stringify.h>
#include <linux/mm.h>
#include <linux/vmalloc.h>
#include <linux/memory.h>
#include <linux/stop_machine.h>
#include <linux/slab.h>
#include <linux/kdebug.h>
#include <linux/kprobes.h>
#include <linux/bsearch.h>
#include <linux/sync_core.h>
#include <asm/text-patching.h>
#include <asm/alternative.h>
#include <asm/sections.h>
#include <asm/pgtable.h>
#include <asm/mce.h>
#include <asm/nmi.h>
#include <asm/cacheflush.h>
#include <asm/tlbflush.h>
#include <asm/insn.h>
#include <asm/io.h>
#include <asm/fixmap.h>
#include <asm/paravirt.h>

int __read_mostly alternatives_patched;

EXPORT_SYMBOL_GPL(alternatives_patched);

#define MAX_PATCH_LEN (255-1)

static int __initdata_or_module debug_alternative;

static int __init debug_alt(char *str)
{
	debug_alternative = 1;
	return 1;
}
__setup("debug-alternative", debug_alt);

static int noreplace_smp;

static int __init setup_noreplace_smp(char *str)
{
	noreplace_smp = 1;
	return 1;
}
__setup("noreplace-smp", setup_noreplace_smp);

#define DPRINTK(fmt, args...)						\
do {									\
	if (debug_alternative)						\
		printk(KERN_DEBUG "%s: " fmt "\n", __func__, ##args);	\
} while (0)

#define DUMP_BYTES(buf, len, fmt, args...)				\
do {									\
	if (unlikely(debug_alternative)) {				\
		int j;							\
									\
		if (!(len))						\
			break;						\
									\
		printk(KERN_DEBUG fmt, ##args);				\
		for (j = 0; j < (len) - 1; j++)				\
			printk(KERN_CONT "%02hhx ", buf[j]);		\
		printk(KERN_CONT "%02hhx\n", buf[j]);			\
	}								\
} while (0)

/*
 * Each GENERIC_NOPX is of X bytes, and defined as an array of bytes
 * that correspond to that nop. Getting from one nop to the next, we
 * add to the array the offset that is equal to the sum of all sizes of
 * nops preceding the one we are after.
 *
 * Note: The GENERIC_NOP5_ATOMIC is at the end, as it breaks the
 * nice symmetry of sizes of the previous nops.
 */
#if defined(GENERIC_NOP1) && !defined(CONFIG_X86_64)
static const unsigned char intelnops[] =
{
	GENERIC_NOP1,
	GENERIC_NOP2,
	GENERIC_NOP3,
	GENERIC_NOP4,
	GENERIC_NOP5,
	GENERIC_NOP6,
	GENERIC_NOP7,
	GENERIC_NOP8,
	GENERIC_NOP5_ATOMIC
};
static const unsigned char * const intel_nops[ASM_NOP_MAX+2] =
{
	NULL,
	intelnops,
	intelnops + 1,
	intelnops + 1 + 2,
	intelnops + 1 + 2 + 3,
	intelnops + 1 + 2 + 3 + 4,
	intelnops + 1 + 2 + 3 + 4 + 5,
	intelnops + 1 + 2 + 3 + 4 + 5 + 6,
	intelnops + 1 + 2 + 3 + 4 + 5 + 6 + 7,
	intelnops + 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8,
};
#endif

#ifdef K8_NOP1
static const unsigned char k8nops[] =
{
	K8_NOP1,
	K8_NOP2,
	K8_NOP3,
	K8_NOP4,
	K8_NOP5,
	K8_NOP6,
	K8_NOP7,
	K8_NOP8,
	K8_NOP5_ATOMIC
};
static const unsigned char * const k8_nops[ASM_NOP_MAX+2] =
{
	NULL,
	k8nops,
	k8nops + 1,
	k8nops + 1 + 2,
	k8nops + 1 + 2 + 3,
	k8nops + 1 + 2 + 3 + 4,
	k8nops + 1 + 2 + 3 + 4 + 5,
	k8nops + 1 + 2 + 3 + 4 + 5 + 6,
	k8nops + 1 + 2 + 3 + 4 + 5 + 6 + 7,
	k8nops + 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8,
};
#endif

#if defined(K7_NOP1) && !defined(CONFIG_X86_64)
static const unsigned char k7nops[] =
{
	K7_NOP1,
	K7_NOP2,
	K7_NOP3,
	K7_NOP4,
	K7_NOP5,
	K7_NOP6,
	K7_NOP7,
	K7_NOP8,
	K7_NOP5_ATOMIC
};
static const unsigned char * const k7_nops[ASM_NOP_MAX+2] =
{
	NULL,
	k7nops,
	k7nops + 1,
	k7nops + 1 + 2,
	k7nops + 1 + 2 + 3,
	k7nops + 1 + 2 + 3 + 4,
	k7nops + 1 + 2 + 3 + 4 + 5,
	k7nops + 1 + 2 + 3 + 4 + 5 + 6,
	k7nops + 1 + 2 + 3 + 4 + 5 + 6 + 7,
	k7nops + 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8,
};
#endif

#ifdef P6_NOP1
static const unsigned char p6nops[] =
{
	P6_NOP1,
	P6_NOP2,
	P6_NOP3,
	P6_NOP4,
	P6_NOP5,
	P6_NOP6,
	P6_NOP7,
	P6_NOP8,
	P6_NOP5_ATOMIC
};
static const unsigned char * const p6_nops[ASM_NOP_MAX+2] =
{
	NULL,
	p6nops,
	p6nops + 1,
	p6nops + 1 + 2,
	p6nops + 1 + 2 + 3,
	p6nops + 1 + 2 + 3 + 4,
	p6nops + 1 + 2 + 3 + 4 + 5,
	p6nops + 1 + 2 + 3 + 4 + 5 + 6,
	p6nops + 1 + 2 + 3 + 4 + 5 + 6 + 7,
	p6nops + 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8,
};
#endif

/* Initialize these to a safe default */
#ifdef CONFIG_X86_64
const unsigned char * const *ideal_nops = p6_nops;
#else
const unsigned char * const *ideal_nops = intel_nops;
#endif

void __init arch_init_ideal_nops(void)
{
	switch (boot_cpu_data.x86_vendor) {
	case X86_VENDOR_INTEL:
		/*
		 * Due to a decoder implementation quirk, some
		 * specific Intel CPUs actually perform better with
		 * the "k8_nops" than with the SDM-recommended NOPs.
		 */
		if (boot_cpu_data.x86 == 6 &&
		    boot_cpu_data.x86_model >= 0x0f &&
		    boot_cpu_data.x86_model != 0x1c &&
		    boot_cpu_data.x86_model != 0x26 &&
		    boot_cpu_data.x86_model != 0x27 &&
		    boot_cpu_data.x86_model < 0x30) {
			ideal_nops = k8_nops;
		} else if (boot_cpu_has(X86_FEATURE_NOPL)) {
			   ideal_nops = p6_nops;
		} else {
#ifdef CONFIG_X86_64
			ideal_nops = k8_nops;
#else
			ideal_nops = intel_nops;
#endif
		}
		break;

	case X86_VENDOR_AMD:
		if (boot_cpu_data.x86 > 0xf) {
			ideal_nops = p6_nops;
			return;
		}

		/* fall through */

	default:
#ifdef CONFIG_X86_64
		ideal_nops = k8_nops;
#else
		if (boot_cpu_has(X86_FEATURE_K8))
			ideal_nops = k8_nops;
		else if (boot_cpu_has(X86_FEATURE_K7))
			ideal_nops = k7_nops;
		else
			ideal_nops = intel_nops;
#endif
	}
}

/* Use this to add nops to a buffer, then text_poke the whole buffer. */
static void __init_or_module add_nops(void *insns, unsigned int len)
{
	while (len > 0) {
		unsigned int noplen = len;
		if (noplen > ASM_NOP_MAX)
			noplen = ASM_NOP_MAX;
		memcpy(insns, ideal_nops[noplen], noplen);
		insns += noplen;
		len -= noplen;
	}
}

extern s32 __return_sites[], __return_sites_end[];
extern struct alt_instr __alt_instructions[], __alt_instructions_end[];
extern s32 __smp_locks[], __smp_locks_end[];
void text_poke_early(void *addr, const void *opcode, size_t len);

/*
 * Are we looking at a near JMP with a 1 or 4-byte displacement.
 */
static inline bool is_jmp(const u8 opcode)
{
	return opcode == 0xeb || opcode == 0xe9;
}

static void __init_or_module
recompute_jump(struct alt_instr *a, u8 *orig_insn, u8 *repl_insn, u8 *insnbuf)
{
	u8 *next_rip, *tgt_rip;
	s32 n_dspl, o_dspl;
	int repl_len;

	if (a->replacementlen != 5)
		return;

	o_dspl = *(s32 *)(insnbuf + 1);

	/* next_rip of the replacement JMP */
	next_rip = repl_insn + a->replacementlen;
	/* target rip of the replacement JMP */
	tgt_rip  = next_rip + o_dspl;
	n_dspl = tgt_rip - orig_insn;

	DPRINTK("target RIP: %px, new_displ: 0x%x", tgt_rip, n_dspl);

	if (tgt_rip - orig_insn >= 0) {
		if (n_dspl - 2 <= 127)
			goto two_byte_jmp;
		else
			goto five_byte_jmp;
	/* negative offset */
	} else {
		if (((n_dspl - 2) & 0xff) == (n_dspl - 2))
			goto two_byte_jmp;
		else
			goto five_byte_jmp;
	}

two_byte_jmp:
	n_dspl -= 2;

	insnbuf[0] = 0xeb;
	insnbuf[1] = (s8)n_dspl;
	add_nops(insnbuf + 2, 3);

	repl_len = 2;
	goto done;

five_byte_jmp:
	n_dspl -= 5;

	insnbuf[0] = 0xe9;
	*(s32 *)&insnbuf[1] = n_dspl;

	repl_len = 5;

done:

	DPRINTK("final displ: 0x%08x, JMP 0x%lx",
		n_dspl, (unsigned long)orig_insn + n_dspl + repl_len);
}

/*
 * "noinline" to cause control flow change and thus invalidate I$ and
 * cause refetch after modification.
 */
static void __init_or_module noinline optimize_nops(struct alt_instr *a, u8 *instr)
{
	unsigned long flags;
	int i;

	for (i = 0; i < a->padlen; i++) {
		if (instr[i] != 0x90)
			return;
	}

	local_irq_save(flags);
	add_nops(instr + (a->instrlen - a->padlen), a->padlen);
	local_irq_restore(flags);

	DUMP_BYTES(instr, a->instrlen, "%px: [%d:%d) optimized NOPs: ",
		   instr, a->instrlen - a->padlen, a->padlen);
}

/*
 * Replace instructions with better alternatives for this CPU type. This runs
 * before SMP is initialized to avoid SMP problems with self modifying code.
 * This implies that asymmetric systems where APs have less capabilities than
 * the boot processor are not handled. Tough. Make sure you disable such
 * features by hand.
 *
 * Marked "noinline" to cause control flow change and thus insn cache
 * to refetch changed I$ lines.
 */
void __init_or_module noinline apply_alternatives(struct alt_instr *start,
						  struct alt_instr *end)
{
	struct alt_instr *a;
	u8 *instr, *replacement;
	u8 insnbuf[MAX_PATCH_LEN];

	DPRINTK("alt table %px, -> %px", start, end);
	/*
	 * The scan order should be from start to end. A later scanned
	 * alternative code can overwrite previously scanned alternative code.
	 * Some kernel functions (e.g. memcpy, memset, etc) use this order to
	 * patch code.
	 *
	 * So be careful if you want to change the scan order to any other
	 * order.
	 */
	for (a = start; a < end; a++) {
		int insnbuf_sz = 0;
		/* Mask away "NOT" flag bit for feature to test. */
		u16 feature = a->cpuid & ~ALTINSTR_FLAG_INV;

		instr = (u8 *)&a->instr_offset + a->instr_offset;
		replacement = (u8 *)&a->repl_offset + a->repl_offset;
		BUG_ON(a->instrlen > sizeof(insnbuf));
		BUG_ON(feature >= (NCAPINTS + NBUGINTS) * 32);

		/*
		 * Patch if either:
		 * - feature is present
		 * - feature not present but ALTINSTR_FLAG_INV is set to mean,
		 *   patch if feature is *NOT* present.
		 */
		if (!boot_cpu_has(feature) == !(a->cpuid & ALTINSTR_FLAG_INV)) {
			if (a->padlen > 1)
				optimize_nops(a, instr);

			continue;
		}

		DPRINTK("feat: %s%d*32+%d, old: (%pS (%px) len: %d), repl: (%px, len: %d), pad: %d",
			(a->cpuid & ALTINSTR_FLAG_INV) ? "!" : "",
			feature >> 5,
			feature & 0x1f,
			instr, instr, a->instrlen,
			replacement, a->replacementlen, a->padlen);

		DUMP_BYTES(instr, a->instrlen, "%px: old_insn: ", instr);
		DUMP_BYTES(replacement, a->replacementlen, "%px: rpl_insn: ", replacement);

		memcpy(insnbuf, replacement, a->replacementlen);
		insnbuf_sz = a->replacementlen;

		/*
		 * 0xe8 is a relative jump; fix the offset.
		 *
		 * Instruction length is checked before the opcode to avoid
		 * accessing uninitialized bytes for zero-length replacements.
		 */
		if (a->replacementlen == 5 && *insnbuf == 0xe8) {
			*(s32 *)(insnbuf + 1) += replacement - instr;
			DPRINTK("Fix CALL offset: 0x%x, CALL 0x%lx",
				*(s32 *)(insnbuf + 1),
				(unsigned long)instr + *(s32 *)(insnbuf + 1) + 5);
		}

		if (a->replacementlen && is_jmp(replacement[0]))
			recompute_jump(a, instr, replacement, insnbuf);

		if (a->instrlen > a->replacementlen) {
			add_nops(insnbuf + a->replacementlen,
				 a->instrlen - a->replacementlen);
			insnbuf_sz += a->instrlen - a->replacementlen;
		}
		DUMP_BYTES(insnbuf, insnbuf_sz, "%px: final_insn: ", instr);

		text_poke_early(instr, insnbuf, insnbuf_sz);
	}
}

#ifdef CONFIG_RETHUNK
/*
 * Rewrite the compiler generated return thunk tail-calls.
 *
 * For example, convert:
 *
 *   JMP __x86_return_thunk
 *
 * into:
 *
 *   RET
 */
static int patch_return(void *addr, struct insn *insn, u8 *bytes)
{
	int i = 0;

	if (cpu_feature_enabled(X86_FEATURE_RETHUNK))
		return -1;

	bytes[i++] = RET_INSN_OPCODE;

	for (; i < insn->length;)
		bytes[i++] = INT3_INSN_OPCODE;

	return i;
}

void __init_or_module noinline apply_returns(s32 *start, s32 *end)
{
	s32 *s;

	for (s = start; s < end; s++) {
		void *addr = (void *)s + *s;
		struct insn insn;
		int len, ret;
		u8 bytes[16];
		u8 op1;

		ret = insn_decode_kernel(&insn, addr);
		if (WARN_ON_ONCE(ret < 0))
			continue;

		op1 = insn.opcode.bytes[0];
		if (WARN_ON_ONCE(op1 != JMP32_INSN_OPCODE))
			continue;

		DPRINTK("return thunk at: %pS (%px) len: %d to: %pS",
			addr, addr, insn.length,
			addr + insn.length + insn.immediate.value);

		len = patch_return(addr, &insn, bytes);
		if (len == insn.length) {
			DUMP_BYTES(((u8*)addr),  len, "%px: orig: ", addr);
			DUMP_BYTES(((u8*)bytes), len, "%px: repl: ", addr);
			text_poke_early(addr, bytes, len);
		}
	}
}
#else
void __init_or_module noinline apply_returns(s32 *start, s32 *end) { }
#endif /* CONFIG_RETHUNK */

#ifdef CONFIG_SMP
static void alternatives_smp_lock(const s32 *start, const s32 *end,
				  u8 *text, u8 *text_end)
{
	const s32 *poff;

	for (poff = start; poff < end; poff++) {
		u8 *ptr = (u8 *)poff + *poff;

		if (!*poff || ptr < text || ptr >= text_end)
			continue;
		/* turn DS segment override prefix into lock prefix */
		if (*ptr == 0x3e)
			text_poke(ptr, ((unsigned char []){0xf0}), 1);
	}
}

static void alternatives_smp_unlock(const s32 *start, const s32 *end,
				    u8 *text, u8 *text_end)
{
	const s32 *poff;

	for (poff = start; poff < end; poff++) {
		u8 *ptr = (u8 *)poff + *poff;

		if (!*poff || ptr < text || ptr >= text_end)
			continue;
		/* turn lock prefix into DS segment override prefix */
		if (*ptr == 0xf0)
			text_poke(ptr, ((unsigned char []){0x3E}), 1);
	}
}

struct smp_alt_module {
	/* what is this ??? */
	struct module	*mod;
	char		*name;

	/* ptrs to lock prefixes */
	const s32	*locks;
	const s32	*locks_end;

	/* .text segment, needed to avoid patching init code ;) */
	u8		*text;
	u8		*text_end;

	struct list_head next;
};
static LIST_HEAD(smp_alt_modules);
static bool uniproc_patched = false;	/* protected by text_mutex */

void __init_or_module alternatives_smp_module_add(struct module *mod,
						  char *name,
						  void *locks, void *locks_end,
						  void *text,  void *text_end)
{
	struct smp_alt_module *smp;

	mutex_lock(&text_mutex);
	if (!uniproc_patched)
		goto unlock;

	if (num_possible_cpus() == 1)
		/* Don't bother remembering, we'll never have to undo it. */
		goto smp_unlock;

	smp = kzalloc(sizeof(*smp), GFP_KERNEL);
	if (NULL == smp)
		/* we'll run the (safe but slow) SMP code then ... */
		goto unlock;

	smp->mod	= mod;
	smp->name	= name;
	smp->locks	= locks;
	smp->locks_end	= locks_end;
	smp->text	= text;
	smp->text_end	= text_end;
	DPRINTK("locks %p -> %p, text %p -> %p, name %s\n",
		smp->locks, smp->locks_end,
		smp->text, smp->text_end, smp->name);

	list_add_tail(&smp->next, &smp_alt_modules);
smp_unlock:
	alternatives_smp_unlock(locks, locks_end, text, text_end);
unlock:
	mutex_unlock(&text_mutex);
}

void __init_or_module alternatives_smp_module_del(struct module *mod)
{
	struct smp_alt_module *item;

	mutex_lock(&text_mutex);
	list_for_each_entry(item, &smp_alt_modules, next) {
		if (mod != item->mod)
			continue;
		list_del(&item->next);
		kfree(item);
		break;
	}
	mutex_unlock(&text_mutex);
}

void alternatives_enable_smp(void)
{
	struct smp_alt_module *mod;

	/* Why bother if there are no other CPUs? */
	BUG_ON(num_possible_cpus() == 1);

	mutex_lock(&text_mutex);

	if (uniproc_patched) {
		pr_info("switching to SMP code\n");
		BUG_ON(num_online_cpus() != 1);
		clear_cpu_cap(&boot_cpu_data, X86_FEATURE_UP);
		clear_cpu_cap(&cpu_data(0), X86_FEATURE_UP);
		list_for_each_entry(mod, &smp_alt_modules, next)
			alternatives_smp_lock(mod->locks, mod->locks_end,
					      mod->text, mod->text_end);
		uniproc_patched = false;
	}
	mutex_unlock(&text_mutex);
}

/*
 * Return 1 if the address range is reserved for SMP-alternatives.
 * Must hold text_mutex.
 */
int alternatives_text_reserved(void *start, void *end)
{
	struct smp_alt_module *mod;
	const s32 *poff;
	u8 *text_start = start;
	u8 *text_end = end;

	lockdep_assert_held(&text_mutex);

	list_for_each_entry(mod, &smp_alt_modules, next) {
		if (mod->text > text_end || mod->text_end < text_start)
			continue;
		for (poff = mod->locks; poff < mod->locks_end; poff++) {
			const u8 *ptr = (const u8 *)poff + *poff;

			if (text_start <= ptr && text_end > ptr)
				return 1;
		}
	}

	return 0;
}
#endif /* CONFIG_SMP */

#ifdef CONFIG_PARAVIRT
void __init_or_module apply_paravirt(struct paravirt_patch_site *start,
				     struct paravirt_patch_site *end)
{
	struct paravirt_patch_site *p;
	char insnbuf[MAX_PATCH_LEN];

	for (p = start; p < end; p++) {
		unsigned int used;

		BUG_ON(p->len > MAX_PATCH_LEN);
		/* prep the buffer with the original instructions */
		memcpy(insnbuf, p->instr, p->len);
		used = pv_init_ops.patch(p->instrtype, insnbuf,
					 (unsigned long)p->instr, p->len);

		BUG_ON(used > p->len);

		/* Pad the rest with nops */
		add_nops(insnbuf + used, p->len - used);
		text_poke_early(p->instr, insnbuf, p->len);
	}
}
extern struct paravirt_patch_site __start_parainstructions[],
	__stop_parainstructions[];
#endif	/* CONFIG_PARAVIRT */

void __init alternative_instructions(void)
{
	/* The patching is not fully atomic, so try to avoid local interruptions
	   that might execute the to be patched code.
	   Other CPUs are not running. */
	stop_nmi();

	/*
	 * Don't stop machine check exceptions while patching.
	 * MCEs only happen when something got corrupted and in this
	 * case we must do something about the corruption.
	 * Ignoring it is worse than an unlikely patching race.
	 * Also machine checks tend to be broadcast and if one CPU
	 * goes into machine check the others follow quickly, so we don't
	 * expect a machine check to cause undue problems during to code
	 * patching.
	 */

	/*
	 * Paravirt patching and alternative patching can be combined to
	 * replace a function call with a short direct code sequence (e.g.
	 * by setting a constant return value instead of doing that in an
	 * external function).
	 * In order to make this work the following sequence is required:
	 * 1. set (artificial) features depending on used paravirt
	 *    functions which can later influence alternative patching
	 * 2. apply paravirt patching (generally replacing an indirect
	 *    function call with a direct one)
	 * 3. apply alternative patching (e.g. replacing a direct function
	 *    call with a custom code sequence)
	 * Doing paravirt patching after alternative patching would clobber
	 * the optimization of the custom code with a function call again.
	 */
	paravirt_set_cap();

	/*
	 * First patch paravirt functions, such that we overwrite the indirect
	 * call with the direct call.
	 */
	apply_paravirt(__parainstructions, __parainstructions_end);
	apply_returns(__return_sites, __return_sites_end);

	/*
	 * Then patch alternatives, such that those paravirt calls that are in
	 * alternatives can be overwritten by their immediate fragments.
	 */
	apply_alternatives(__alt_instructions, __alt_instructions_end);

#ifdef CONFIG_SMP
	/* Patch to UP if other cpus not imminent. */
	if (!noreplace_smp && (num_present_cpus() == 1 || setup_max_cpus <= 1)) {
		uniproc_patched = true;
		alternatives_smp_module_add(NULL, "core kernel",
					    __smp_locks, __smp_locks_end,
					    _text, _etext);
	}

	if (!uniproc_patched || num_possible_cpus() == 1)
		free_init_pages("SMP alternatives",
				(unsigned long)__smp_locks,
				(unsigned long)__smp_locks_end);
#endif

	restart_nmi();
	alternatives_patched = 1;
}

/**
 * text_poke_early - Update instructions on a live kernel at boot time
 * @addr: address to modify
 * @opcode: source of the copy
 * @len: length to copy
 *
 * When you use this code to patch more than one byte of an instruction
 * you need to make sure that other CPUs cannot execute this code in parallel.
 * Also no thread must be currently preempted in the middle of these
 * instructions. And on the local CPU you need to be protected against NMI or
 * MCE handlers seeing an inconsistent instruction while you patch.
 */
void __init_or_module text_poke_early(void *addr, const void *opcode,
				      size_t len)
{
	unsigned long flags;

	if (boot_cpu_has(X86_FEATURE_NX) &&
	    is_module_text_address((unsigned long)addr)) {
		/*
		 * Modules text is marked initially as non-executable, so the
		 * code cannot be running and speculative code-fetches are
		 * prevented. Just change the code.
		 */
		memcpy(addr, opcode, len);
	} else {
		local_irq_save(flags);
		memcpy(addr, opcode, len);
		local_irq_restore(flags);
		sync_core();

		/*
		 * Could also do a CLFLUSH here to speed up CPU recovery; but
		 * that causes hangs on some VIA CPUs.
		 */
	}
}

__ro_after_init struct mm_struct *poking_mm;
__ro_after_init unsigned long poking_addr;

static void *__text_poke(void *addr, const void *opcode, size_t len)
{
	unsigned long flags;
	char *vaddr;
	struct page *pages[2];
	int i;

	/*
	 * While boot memory allocator is runnig we cannot use struct
	 * pages as they are not yet initialized.
	 */
	BUG_ON(!after_bootmem);

	if (!core_kernel_text((unsigned long)addr)) {
		pages[0] = vmalloc_to_page(addr);
		pages[1] = vmalloc_to_page(addr + PAGE_SIZE);
	} else {
		pages[0] = virt_to_page(addr);
		WARN_ON(!PageReserved(pages[0]));
		pages[1] = virt_to_page(addr + PAGE_SIZE);
	}
	BUG_ON(!pages[0]);
	local_irq_save(flags);
	set_fixmap(FIX_TEXT_POKE0, page_to_phys(pages[0]));
	if (pages[1])
		set_fixmap(FIX_TEXT_POKE1, page_to_phys(pages[1]));
	vaddr = (char *)fix_to_virt(FIX_TEXT_POKE0);
	memcpy(&vaddr[(unsigned long)addr & ~PAGE_MASK], opcode, len);
	clear_fixmap(FIX_TEXT_POKE0);
	if (pages[1])
		clear_fixmap(FIX_TEXT_POKE1);
	local_flush_tlb();
	sync_core();
	/* Could also do a CLFLUSH here to speed up CPU recovery; but
	   that causes hangs on some VIA CPUs. */
	for (i = 0; i < len; i++)
		BUG_ON(((char *)addr)[i] != ((char *)opcode)[i]);
	local_irq_restore(flags);
	return addr;
}

/**
 * text_poke - Update instructions on a live kernel
 * @addr: address to modify
 * @opcode: source of the copy
 * @len: length to copy
 *
 * Only atomic text poke/set should be allowed when not doing early patching.
 * It means the size must be writable atomically and the address must be aligned
 * in a way that permits an atomic write. It also makes sure we fit on a single
 * page.
 */
void *text_poke(void *addr, const void *opcode, size_t len)
{
	lockdep_assert_held(&text_mutex);

	return __text_poke(addr, opcode, len);
}

/**
 * text_poke_kgdb - Update instructions on a live kernel by kgdb
 * @addr: address to modify
 * @opcode: source of the copy
 * @len: length to copy
 *
 * Only atomic text poke/set should be allowed when not doing early patching.
 * It means the size must be writable atomically and the address must be aligned
 * in a way that permits an atomic write. It also makes sure we fit on a single
 * page.
 *
 * Context: should only be used by kgdb, which ensures no other core is running,
 *	    despite the fact it does not hold the text_mutex.
 */
void *text_poke_kgdb(void *addr, const void *opcode, size_t len)
{
	return __text_poke(addr, opcode, len);
}

static void do_sync_core(void *info)
{
	sync_core();
}

void text_poke_sync(void)
{
	on_each_cpu(do_sync_core, NULL, 1);
}

struct text_poke_loc {
	/* addr := _stext + rel_addr */
	s32 rel_addr;
	s32 disp;
	u8 len;
	u8 opcode;
	const u8 text[POKE_MAX_OPCODE_SIZE];
	/* see text_poke_bp_batch() */
	u8 old;
};

struct bp_patching_desc {
	struct text_poke_loc *vec;
	int nr_entries;
	atomic_t refs;
};

static struct bp_patching_desc *bp_desc;

static inline struct bp_patching_desc *try_get_desc(struct bp_patching_desc **descp)
{
	/* rcu_dereference */
	struct bp_patching_desc *desc = READ_ONCE(*descp);

	if (!desc || !atomic_inc_not_zero(&desc->refs))
		return NULL;

	return desc;
}

static inline void put_desc(struct bp_patching_desc *desc)
{
	smp_mb__before_atomic();
	atomic_dec(&desc->refs);
}

static inline void *text_poke_addr(struct text_poke_loc *tp)
{
	return _stext + tp->rel_addr;
}

static int notrace patch_cmp(const void *key, const void *elt)
{
	struct text_poke_loc *tp = (struct text_poke_loc *) elt;

	if (key < text_poke_addr(tp))
		return -1;
	if (key > text_poke_addr(tp))
		return 1;
	return 0;
}
NOKPROBE_SYMBOL(patch_cmp);

int notrace poke_int3_handler(struct pt_regs *regs)
{
	struct bp_patching_desc *desc;
	struct text_poke_loc *tp;
	int ret = 0;
	void *ip;

	if (user_mode(regs))
		return 0;

	/*
	 * Having observed our INT3 instruction, we now must observe
	 * bp_desc:
	 *
	 *	bp_desc = desc			INT3
	 *	WMB				RMB
	 *	write INT3			if (desc)
	 */
	smp_rmb();

	desc = try_get_desc(&bp_desc);
	if (!desc)
		return 0;

	/*
	 * Discount the INT3. See text_poke_bp_batch().
	 */
	ip = (void *) regs->ip - INT3_INSN_SIZE;

	/*
	 * Skip the binary search if there is a single member in the vector.
	 */
	if (unlikely(desc->nr_entries > 1)) {
		tp = bsearch(ip, desc->vec, desc->nr_entries,
			     sizeof(struct text_poke_loc),
			     patch_cmp);
		if (!tp)
			goto out_put;
	} else {
		tp = desc->vec;
		if (text_poke_addr(tp) != ip)
			goto out_put;
	}

	ip += tp->len;

	switch (tp->opcode) {
	case INT3_INSN_OPCODE:
		/*
		 * Someone poked an explicit INT3, they'll want to handle it,
		 * do not consume.
		 */
		goto out_put;

	case RET_INSN_OPCODE:
		int3_emulate_ret(regs);
		break;

	case CALL_INSN_OPCODE:
		int3_emulate_call(regs, (long)ip + tp->disp);
		break;

	case JMP32_INSN_OPCODE:
	case JMP8_INSN_OPCODE:
		int3_emulate_jmp(regs, (long)ip + tp->disp);
		break;

	default:
		BUG();
	}

	ret = 1;

out_put:
	put_desc(desc);
	return ret;
}
NOKPROBE_SYMBOL(poke_int3_handler);

#define TP_VEC_MAX (PAGE_SIZE / sizeof(struct text_poke_loc))
static struct text_poke_loc tp_vec[TP_VEC_MAX];
static int tp_vec_nr;

/**
 * text_poke_bp_batch() -- update instructions on live kernel on SMP
 * @tp:			vector of instructions to patch
 * @nr_entries:		number of entries in the vector
 *
 * Modify multi-byte instruction by using int3 breakpoint on SMP.
 * We completely avoid stop_machine() here, and achieve the
 * synchronization using int3 breakpoint.
 *
 * The way it is done:
 *	- For each entry in the vector:
 *		- add a int3 trap to the address that will be patched
 *	- sync cores
 *	- For each entry in the vector:
 *		- update all but the first byte of the patched range
 *	- sync cores
 *	- For each entry in the vector:
 *		- replace the first byte (int3) by the first byte of
 *		  replacing opcode
 *	- sync cores
 */
static void text_poke_bp_batch(struct text_poke_loc *tp, unsigned int nr_entries)
{
	struct bp_patching_desc desc = {
		.vec = tp,
		.nr_entries = nr_entries,
		.refs = ATOMIC_INIT(1),
	};
	unsigned char int3 = INT3_INSN_OPCODE;
	unsigned int i;
	int do_sync;

	lockdep_assert_held(&text_mutex);

	smp_store_release(&bp_desc, &desc); /* rcu_assign_pointer */

	/*
	 * Corresponding read barrier in int3 notifier for making sure the
	 * nr_entries and handler are correctly ordered wrt. patching.
	 */
	smp_wmb();

	/*
	 * First step: add a int3 trap to the address that will be patched.
	 */
	for (i = 0; i < nr_entries; i++) {
		tp[i].old = *(u8 *)text_poke_addr(&tp[i]);
		text_poke(text_poke_addr(&tp[i]), &int3, INT3_INSN_SIZE);
	}

	text_poke_sync();

	/*
	 * Second step: update all but the first byte of the patched range.
	 */
	for (do_sync = 0, i = 0; i < nr_entries; i++) {
		u8 old[POKE_MAX_OPCODE_SIZE] = { tp[i].old, };
		int len = tp[i].len;

		if (len - INT3_INSN_SIZE > 0) {
			memcpy(old + INT3_INSN_SIZE,
			       text_poke_addr(&tp[i]) + INT3_INSN_SIZE,
			       len - INT3_INSN_SIZE);
			text_poke(text_poke_addr(&tp[i]) + INT3_INSN_SIZE,
				  (const char *)tp[i].text + INT3_INSN_SIZE,
				  len - INT3_INSN_SIZE);
			do_sync++;
		}

		/*
		 * Emit a perf event to record the text poke, primarily to
		 * support Intel PT decoding which must walk the executable code
		 * to reconstruct the trace. The flow up to here is:
		 *   - write INT3 byte
		 *   - IPI-SYNC
		 *   - write instruction tail
		 * At this point the actual control flow will be through the
		 * INT3 and handler and not hit the old or new instruction.
		 * Intel PT outputs FUP/TIP packets for the INT3, so the flow
		 * can still be decoded. Subsequently:
		 *   - emit RECORD_TEXT_POKE with the new instruction
		 *   - IPI-SYNC
		 *   - write first byte
		 *   - IPI-SYNC
		 * So before the text poke event timestamp, the decoder will see
		 * either the old instruction flow or FUP/TIP of INT3. After the
		 * text poke event timestamp, the decoder will see either the
		 * new instruction flow or FUP/TIP of INT3. Thus decoders can
		 * use the timestamp as the point at which to modify the
		 * executable code.
		 * The old instruction is recorded so that the event can be
		 * processed forwards or backwards.
		 */
		perf_event_text_poke(text_poke_addr(&tp[i]), old, len,
				     tp[i].text, len);
	}

	if (do_sync) {
		/*
		 * According to Intel, this core syncing is very likely
		 * not necessary and we'd be safe even without it. But
		 * better safe than sorry (plus there's not only Intel).
		 */
		text_poke_sync();
	}

	/*
	 * Third step: replace the first byte (int3) by the first byte of
	 * replacing opcode.
	 */
	for (do_sync = 0, i = 0; i < nr_entries; i++) {
		if (tp[i].text[0] == INT3_INSN_OPCODE)
			continue;

		text_poke(text_poke_addr(&tp[i]), tp[i].text, INT3_INSN_SIZE);
		do_sync++;
	}

	if (do_sync)
		text_poke_sync();

	/*
	 * Remove and synchronize_rcu(), except we have a very primitive
	 * refcount based completion.
	 */
	WRITE_ONCE(bp_desc, NULL); /* RCU_INIT_POINTER */
	if (!atomic_dec_and_test(&desc.refs))
		atomic_cond_read_acquire(&desc.refs, !VAL);
}

void text_poke_loc_init(struct text_poke_loc *tp, void *addr,
			const void *opcode, size_t len, const void *emulate)
{
	struct insn insn;
	int ret, i;

	memcpy((void *)tp->text, opcode, len);
	if (!emulate)
		emulate = opcode;

	ret = insn_decode_kernel(&insn, emulate);
	BUG_ON(ret < 0);

	tp->rel_addr = addr - (void *)_stext;
	tp->len = len;
	tp->opcode = insn.opcode.bytes[0];

	switch (tp->opcode) {
	case RET_INSN_OPCODE:
	case JMP32_INSN_OPCODE:
	case JMP8_INSN_OPCODE:
		/*
		 * Control flow instructions without implied execution of the
		 * next instruction can be padded with INT3.
		 */
		for (i = insn.length; i < len; i++)
			BUG_ON(tp->text[i] != INT3_INSN_OPCODE);
		break;

	default:
		BUG_ON(len != insn.length);
	};


	switch (tp->opcode) {
	case INT3_INSN_OPCODE:
	case RET_INSN_OPCODE:
		break;

	case CALL_INSN_OPCODE:
	case JMP32_INSN_OPCODE:
	case JMP8_INSN_OPCODE:
		tp->disp = insn.immediate.value;
		break;

	default: /* assume NOP */
		switch (len) {
		case 2: /* NOP2 -- emulate as JMP8+0 */
			BUG_ON(memcmp(emulate, ideal_nops[len], len));
			tp->opcode = JMP8_INSN_OPCODE;
			tp->disp = 0;
			break;

		case 5: /* NOP5 -- emulate as JMP32+0 */
			BUG_ON(memcmp(emulate, ideal_nops[NOP_ATOMIC5], len));
			tp->opcode = JMP32_INSN_OPCODE;
			tp->disp = 0;
			break;

		default: /* unknown instruction */
			BUG();
		}
		break;
	}
}

/*
 * We hard rely on the tp_vec being ordered; ensure this is so by flushing
 * early if needed.
 */
static bool tp_order_fail(void *addr)
{
	struct text_poke_loc *tp;

	if (!tp_vec_nr)
		return false;

	if (!addr) /* force */
		return true;

	tp = &tp_vec[tp_vec_nr - 1];
	if ((unsigned long)text_poke_addr(tp) > (unsigned long)addr)
		return true;

	return false;
}

static void text_poke_flush(void *addr)
{
	if (tp_vec_nr == TP_VEC_MAX || tp_order_fail(addr)) {
		text_poke_bp_batch(tp_vec, tp_vec_nr);
		tp_vec_nr = 0;
	}
}

void text_poke_finish(void)
{
	text_poke_flush(NULL);
}

void __ref text_poke_queue(void *addr, const void *opcode, size_t len, const void *emulate)
{
	struct text_poke_loc *tp;

	if (unlikely(system_state == SYSTEM_BOOTING)) {
		text_poke_early(addr, opcode, len);
		return;
	}

	text_poke_flush(addr);

	tp = &tp_vec[tp_vec_nr++];
	text_poke_loc_init(tp, addr, opcode, len, emulate);
}

/**
 * text_poke_bp() -- update instructions on live kernel on SMP
 * @addr:	address to patch
 * @opcode:	opcode of new instruction
 * @len:	length to copy
 * @handler:	address to jump to when the temporary breakpoint is hit
 *
 * Update a single instruction with the vector in the stack, avoiding
 * dynamically allocated memory. This function should be used when it is
 * not possible to allocate memory.
 */
void __ref text_poke_bp(void *addr, const void *opcode, size_t len, const void *emulate)
{
	struct text_poke_loc tp;

	if (unlikely(system_state == SYSTEM_BOOTING)) {
		text_poke_early(addr, opcode, len);
		return;
	}

	text_poke_loc_init(&tp, addr, opcode, len, emulate);
	text_poke_bp_batch(&tp, 1);
}
