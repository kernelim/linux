/*
 *  arch/s390/kernel/processor.c
 *
 *  Copyright IBM Corp. 2008
 *  Author(s): Martin Schwidefsky (schwidefsky@de.ibm.com)
 */

#define KMSG_COMPONENT "cpu"
#define pr_fmt(fmt) KMSG_COMPONENT ": " fmt

#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/smp.h>
#include <linux/seq_file.h>
#include <linux/delay.h>

#include <asm/elf.h>
#include <asm/lowcore.h>
#include <asm/param.h>
#include <asm/system.h>

void __cpuinit print_cpu_info(void)
{
	pr_info("Processor %d started, address %d, identification %06X\n",
		S390_lowcore.cpu_nr, S390_lowcore.cpu_addr,
		S390_lowcore.cpu_id.ident);
}

static void show_facilities(struct seq_file *m)
{
	unsigned long long *facility_bits;
	int dwords, bit, i;

	facility_bits = kzalloc(32 * BITS_PER_LONG, GFP_KERNEL);
	if (!facility_bits)
		return;

	dwords = stfle(facility_bits, 32);
	if (dwords < 0)
		goto out;

	seq_puts(m, "facilities      :");
	for (i = 0; i < min(dwords, 32); i++)
		for (bit = 0; bit < BITS_PER_LONG; bit++)
			if (facility_bits[i] &
			    (1ULL << (BITS_PER_LONG - 1 - bit)))
				seq_printf(m, " %d", BITS_PER_LONG * i + bit);
	seq_putc(m, '\n');
out:
	kfree(facility_bits);
}

/*
 * show_cpuinfo - Get information on one CPU for use by procfs.
 */

static int show_cpuinfo(struct seq_file *m, void *v)
{
	static const char *hwcap_str[11] = {
		"esan3", "zarch", "stfle", "msa", "ldisp", "eimm", "dfp",
		"edat", "etf3eh", "highgprs", "te"
	};
	struct _lowcore *lc;
	unsigned long n = (unsigned long) v - 1;
	int i;

	s390_adjust_jiffies();
	preempt_disable();
	if (!n) {
		seq_printf(m, "vendor_id       : IBM/S390\n"
			   "# processors    : %i\n"
			   "bogomips per cpu: %lu.%02lu\n",
			   num_online_cpus(), loops_per_jiffy/(500000/HZ),
			   (loops_per_jiffy/(5000/HZ))%100);
		seq_puts(m, "features\t: ");
		for (i = 0; i < 11; i++)
			if (hwcap_str[i] && (elf_hwcap & (1UL << i)))
				seq_printf(m, "%s ", hwcap_str[i]);
		seq_puts(m, "\n");
		show_facilities(m);
	}

	if (cpu_online(n)) {
#ifdef CONFIG_SMP
		lc = (smp_processor_id() == n) ?
			&S390_lowcore : lowcore_ptr[n];
#else
		lc = &S390_lowcore;
#endif
		seq_printf(m, "processor %li: "
			   "version = %02X,  "
			   "identification = %06X,  "
			   "machine = %04X\n",
			   n, lc->cpu_id.version,
			   lc->cpu_id.ident,
			   lc->cpu_id.machine);
	}
	preempt_enable();
	return 0;
}

static void *c_start(struct seq_file *m, loff_t *pos)
{
	return *pos < NR_CPUS ? (void *)((unsigned long) *pos + 1) : NULL;
}

static void *c_next(struct seq_file *m, void *v, loff_t *pos)
{
	++*pos;
	return c_start(m, pos);
}

static void c_stop(struct seq_file *m, void *v)
{
}

const struct seq_operations cpuinfo_op = {
	.start	= c_start,
	.next	= c_next,
	.stop	= c_stop,
	.show	= show_cpuinfo,
};

int s390_isolate_bp(void)
{
	unsigned long long facility_bits[2];
	int nr_facilities;

	nr_facilities = min(stfle(facility_bits, 2), 2) * BITS_PER_LONG;
	facility_bits[1] &= ~(1ULL << 46);
	if (nr_facilities < 2 || !(facility_bits[1] & (1ULL << 45)))
		return -EOPNOTSUPP;
	set_thread_flag(TIF_ISOLATE_BP);
	return 0;
}
EXPORT_SYMBOL(s390_isolate_bp);

int s390_isolate_bp_guest(void)
{
	unsigned long long facility_bits[2];
	int nr_facilities;

	nr_facilities = min(stfle(facility_bits, 2), 2) * BITS_PER_LONG;
	facility_bits[1] &= ~(1ULL << 46);
	if (nr_facilities < 2 || !(facility_bits[1] & (1ULL << 45)))
		return -EOPNOTSUPP;
	set_thread_flag(TIF_ISOLATE_BP_GUEST);
	return 0;
}
EXPORT_SYMBOL(s390_isolate_bp_guest);
