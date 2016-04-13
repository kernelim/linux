/*
 *  HW NMI watchdog support
 *
 *  started by Don Zickus, Copyright (C) 2010 Red Hat, Inc.
 *
 *  Arch specific calls to support NMI watchdog
 *
 *  Bits copied from original nmi.c file
 *
 */
#include <asm/apic.h>

#include <linux/cpumask.h>
#include <linux/kdebug.h>
#include <linux/notifier.h>
#include <linux/kprobes.h>
#include <linux/nmi.h>
#include <linux/module.h>
#include <linux/seq_buf.h>

u64 hw_nmi_get_sample_period(void)
{
	return (u64)(cpu_khz) * 1000 * 60;
}

/* For reliability, we're prepared to waste bits here. */
static DECLARE_BITMAP(backtrace_mask, NR_CPUS) __read_mostly;
static cpumask_t printtrace_mask;

#define NMI_BUF_SIZE		4096

struct nmi_seq_buf {
	unsigned char		buffer[NMI_BUF_SIZE];
	struct seq_buf		seq;
};

/* Safe printing in NMI context */
static DEFINE_PER_CPU(struct nmi_seq_buf, nmi_print_seq);

/* "in progress" flag of arch_trigger_all_cpu_backtrace */
static unsigned long backtrace_flag;

static void print_seq_line(struct nmi_seq_buf *s, int start, int end)
{
	const char *buf = s->buffer + start;

	printk("%.*s", (end - start) + 1, buf);
}

void arch_trigger_all_cpu_backtrace(bool include_self)
{
	struct nmi_seq_buf *s;
	int len;
	int cpu;
	int i;
	int this_cpu = get_cpu();

	if (test_and_set_bit(0, &backtrace_flag)) {
		/*
		 * If there is already a trigger_all_cpu_backtrace() in progress
		 * (backtrace_flag == 1), don't output double cpu dump infos.
		 */
		put_cpu();
		return;
	}

	cpumask_copy(to_cpumask(backtrace_mask), cpu_online_mask);
	if (!include_self)
		cpumask_clear_cpu(this_cpu, to_cpumask(backtrace_mask));

	cpumask_copy(&printtrace_mask, to_cpumask(backtrace_mask));
	/*
	 * Set up per_cpu seq_buf buffers that the NMIs running on the other
	 * CPUs will write to.
	 */
	for_each_cpu(cpu, to_cpumask(backtrace_mask)) {
		s = &per_cpu(nmi_print_seq, cpu);
		seq_buf_init(&s->seq, s->buffer, NMI_BUF_SIZE);
	}

	if (!cpumask_empty(to_cpumask(backtrace_mask))) {
		pr_info("sending NMI to %s CPUs:\n",
			(include_self ? "all" : "other"));
		apic->send_IPI_mask(to_cpumask(backtrace_mask), NMI_VECTOR);
	}

	/* Wait for up to 10 seconds for all CPUs to do the backtrace */
	for (i = 0; i < 10 * 1000; i++) {
		if (cpumask_empty(to_cpumask(backtrace_mask)))
			break;
		mdelay(1);
		touch_softlockup_watchdog();
	}

	/*
	 * Now that all the NMIs have triggered, we can dump out their
	 * back traces safely to the console.
	 */
	for_each_cpu(cpu, &printtrace_mask) {
		int last_i = 0;

		s = &per_cpu(nmi_print_seq, cpu);
		len = seq_buf_used(&s->seq);
		if (!len)
			continue;

		/* Print line by line. */
		for (i = 0; i < len; i++) {
			if (s->buffer[i] == '\n') {
				print_seq_line(s, last_i, i);
				last_i = i + 1;
			}
		}
		/* Check if there was a partial line. */
		if (last_i < len) {
			print_seq_line(s, last_i, len - 1);
			pr_cont("\n");
		}
	}

	clear_bit(0, &backtrace_flag);
	smp_mb__after_clear_bit();
	put_cpu();
}

/*
 * It is not safe to call printk() directly from NMI handlers.
 * It may be fine if the NMI detected a lock up and we have no choice
 * but to do so, but doing a NMI on all other CPUs to get a back trace
 * can be done with a sysrq-l. We don't want that to lock up, which
 * can happen if the NMI interrupts a printk in progress.
 *
 * Instead, we redirect the vprintk() to this nmi_vprintk() that writes
 * the content into a per cpu seq_buf buffer. Then when the NMIs are
 * all done, we can safely dump the contents of the seq_buf to a printk()
 * from a non NMI context.
 */
static int nmi_vprintk(const char *fmt, va_list args)
{
	struct nmi_seq_buf *s = &__get_cpu_var(nmi_print_seq);
	unsigned int len = seq_buf_used(&s->seq);

	seq_buf_vprintf(&s->seq, fmt, args);
	return seq_buf_used(&s->seq) - len;
}

static int __kprobes
arch_trigger_all_cpu_backtrace_handler(struct notifier_block *self,
			 unsigned long cmd, void *__args)
{
	struct die_args *args = __args;
	struct pt_regs *regs;
	int cpu = smp_processor_id();

	switch (cmd) {
	case DIE_NMI:
	case DIE_NMI_IPI:
		break;

	default:
		return NOTIFY_DONE;
	}

	regs = args->regs;

	if (cpumask_test_cpu(cpu, to_cpumask(backtrace_mask))) {
		printk_func_t printk_func_save = __get_cpu_var(printk_func);

		/* Replace printk to write into the NMI seq */
		__get_cpu_var(printk_func) = nmi_vprintk;
		printk(KERN_WARNING "NMI backtrace for cpu %d\n", cpu);
		show_regs(regs);
		dump_stack();
		__get_cpu_var(printk_func) = printk_func_save;

		cpumask_clear_cpu(cpu, to_cpumask(backtrace_mask));
		return NOTIFY_STOP;
	}

	return NOTIFY_DONE;
}

static __read_mostly struct notifier_block backtrace_notifier = {
	.notifier_call          = arch_trigger_all_cpu_backtrace_handler,
	.next                   = NULL,
	.priority               = NMI_LOCAL_LOW_PRIOR,
};

static int __init register_trigger_all_cpu_backtrace(void)
{
	register_die_notifier(&backtrace_notifier);
	return 0;
}
early_initcall(register_trigger_all_cpu_backtrace);

/* STUB calls to mimic old nmi_watchdog behaviour */
#if defined(CONFIG_X86_LOCAL_APIC)
unsigned int nmi_watchdog = NMI_NONE;
EXPORT_SYMBOL(nmi_watchdog);
void acpi_nmi_enable(void) { return; }
void acpi_nmi_disable(void) { return; }
#endif
atomic_t nmi_active = ATOMIC_INIT(0);           /* oprofile uses this */
EXPORT_SYMBOL(nmi_active);
void cpu_nmi_set_wd_enabled(void) { return; }
void stop_apic_nmi_watchdog(void *unused) { return; }
void setup_apic_nmi_watchdog(void *unused) { return; }
int __init check_nmi_watchdog(void) { return 0; }
void __cpuinit nmi_watchdog_default(void) { return; }
