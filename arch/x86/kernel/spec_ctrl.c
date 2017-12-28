/*
 *  Copyright (C) 2017  Red Hat, Inc.
 *
 *  This work is licensed under the terms of the GNU GPL, version 2. See
 *  the COPYING file in the top-level directory.
 */

#include <linux/cpu.h>
#include <linux/percpu.h>
#include <linux/debugfs.h>
#include <linux/uaccess.h>
#include <asm/spec_ctrl.h>
#include <asm/cpufeature.h>

static DEFINE_MUTEX(spec_ctrl_mutex);

enum {
	IBRS_DISABLED,
	/* in host kernel, disabled in guest and userland */
	IBRS_ENABLED,
	/* in host kernel and host userland, disabled in guest */
	IBRS_ENABLED_USER,
	IBRS_MAX = IBRS_ENABLED_USER,
};
static unsigned int ibrs_enabled __read_mostly;
static bool noibrs_cmdline __read_mostly;

#define IBPB_ENABLED_ONLY_DEFAULT 1
enum {
	IBPB_DISABLED,
	IBPB_ENABLED,
	IBPB_ENABLED_ONLY, /* use only IBPB instead of IBRS */
	IBPB_MAX = IBPB_ENABLED_ONLY,
};
static unsigned int ibpb_enabled __read_mostly;
static bool noibpb_cmdline __read_mostly;

#define USE_IBP_DISABLE_DEFAULT 1
static bool use_ibp_disable __read_mostly;

static void set_spec_ctrl_pcp(bool enable, int flag)
{
	int cpu, val = percpu_read(spec_ctrl_pcp);
	if (enable)
		val |= flag;
	else
		val &= ~flag;
	for_each_possible_cpu(cpu)
		WRITE_ONCE(per_cpu(spec_ctrl_pcp, cpu), val);
}

void set_spec_ctrl_pcp_ibrs(bool enable)
{
	set_spec_ctrl_pcp(enable, SPEC_CTRL_PCP_IBRS);
}

void set_spec_ctrl_pcp_ibrs_user(bool enable)
{
	set_spec_ctrl_pcp(enable, SPEC_CTRL_PCP_IBRS_USER);
}

void set_spec_ctrl_pcp_ibpb(bool enable)
{
	set_spec_ctrl_pcp(enable, SPEC_CTRL_PCP_IBPB);
}

void set_spec_ctrl_pcp_only_ibpb(bool enable)
{
	set_spec_ctrl_pcp(enable, SPEC_CTRL_PCP_ONLY_IBPB);
}

static void spec_ctrl_sync_all_cpus(u32 msr_nr, u64 val)
{
	int cpu;
	get_online_cpus();
	for_each_online_cpu(cpu)
		wrmsrl_on_cpu(cpu, msr_nr, val);
	put_online_cpus();
}

static void sync_all_cpus_ibrs(bool enable)
{
	spec_ctrl_sync_all_cpus(MSR_IA32_SPEC_CTRL,
				 enable ? FEATURE_ENABLE_IBRS : 0);
}

static void __sync_this_cpu_ibp(void *data)
{
	bool enable = *(bool *)data;
	u64 val;

	/* disable IBP on old CPU families */
	rdmsrl(MSR_F15H_IC_CFG, val);
	if (!enable)
		val |= MSR_F15H_IC_CFG_DIS_IND;
	else
		val &= ~MSR_F15H_IC_CFG_DIS_IND;
	wrmsrl(MSR_F15H_IC_CFG, val);
}

/* enable means IBP should be enabled in the CPU (i.e. fast) */
static void sync_all_cpus_ibp(bool enable)
{
	get_online_cpus();

	__sync_this_cpu_ibp(&enable);

	smp_call_function_many(cpu_online_mask, __sync_this_cpu_ibp,
			       &enable, 1);

	put_online_cpus();
}

static int __init noibrs(char *str)
{
	noibrs_cmdline = true;

	return 0;
}
early_param("noibrs", noibrs);

static int __init noibpb(char *str)
{
	noibpb_cmdline = true;

	return 0;
}
early_param("noibpb", noibpb);

/* this is called when secondary CPUs come online */
void spec_ctrl_cpu_init(void)
{
	if (use_ibp_disable) {
		bool enabled = !ibrs_enabled;
		__sync_this_cpu_ibp(&enabled);
		return;
	}

	/*
	 * If ibrs_enabled == 2 kernel entry points won't set IBRS so
	 * set it during secondary CPU startup.
	 */
	if (cpu_has_spec_ctrl() &&
	    percpu_read(spec_ctrl_pcp) & SPEC_CTRL_PCP_IBRS_USER)
		native_wrmsrl(MSR_IA32_SPEC_CTRL, FEATURE_ENABLE_IBRS);
}

void spec_ctrl_init(struct cpuinfo_x86 *c)
{
	if (c->x86_vendor != X86_VENDOR_INTEL &&
	    c->x86_vendor != X86_VENDOR_AMD)
		return;

	if (c != &boot_cpu_data) {
		spec_ctrl_cpu_init();
		return;
	}

	/*
	 * Some AMD CPUs don't need IBPB or IBRS CPUID bits, because
	 * they can just disable indirect branch predictor
	 * support (MSR 0xc0011021[14]).
	 */
	if (c->x86_vendor == X86_VENDOR_AMD &&
	    !(boot_cpu_has(X86_FEATURE_IBPB_SUPPORT) ||
	      cpu_has_spec_ctrl()) &&
	    !(noibpb_cmdline && noibrs_cmdline)) {
		switch (c->x86) {
		case 0x10:
		case 0x12:
		case 0x16:
			if (!use_ibp_disable) {
				use_ibp_disable = true;
				if (USE_IBP_DISABLE_DEFAULT) {
					/* default enabled */
					ibrs_enabled = IBRS_ENABLED_USER;
					ibpb_enabled = IBPB_ENABLED;
				}

				printk("FEATURE SPEC_CTRL Present "
				       "(Implicit)\n");
				printk("FEATURE IBPB_SUPPORT Present "
				       "(Implicit)\n");
			}
			spec_ctrl_cpu_init();
			break;
		}
	}

	if (use_ibp_disable)
		return;

	/*
	 * On both Intel and AMD, SPEC_CTRL implies IBPB.
	 */
	if (cpu_has_spec_ctrl()) {
		setup_force_cpu_cap(X86_FEATURE_IBPB_SUPPORT);
		if (!ibrs_enabled && !noibrs_cmdline) {
			set_spec_ctrl_pcp_ibrs(true);
			ibrs_enabled = IBRS_ENABLED;
		}
		printk_once(KERN_INFO "FEATURE SPEC_CTRL Present\n");
		spec_ctrl_cpu_init();
	} else {
		printk_once(KERN_INFO "FEATURE SPEC_CTRL Not Present\n");
	}

	if (boot_cpu_has(X86_FEATURE_IBPB_SUPPORT)) {
		if (!ibpb_enabled && !noibpb_cmdline) {
			set_spec_ctrl_pcp_ibpb(true);
			ibpb_enabled = IBPB_ENABLED;
			if (IBPB_ENABLED_ONLY_DEFAULT &&
			    !cpu_has_spec_ctrl() && !ibrs_enabled) {
				set_spec_ctrl_pcp_only_ibpb(true);
				ibpb_enabled = IBPB_ENABLED_ONLY;
			}
		}
		printk_once(KERN_INFO "FEATURE IBPB_SUPPORT Present\n");
	} else {
		printk_once(KERN_INFO "FEATURE IBPB_SUPPORT Not Present\n");
	}
}

void spec_ctrl_rescan_cpuid(void)
{
	if (use_ibp_disable)
		return;
	mutex_lock(&spec_ctrl_mutex);
	if (boot_cpu_data.x86_vendor == X86_VENDOR_INTEL ||
	    boot_cpu_data.x86_vendor == X86_VENDOR_AMD) {
		/* detect spec ctrl related cpuid additions */
		init_scattered_cpuid_features(&boot_cpu_data);
		spec_ctrl_init(&boot_cpu_data);
	}
	mutex_unlock(&spec_ctrl_mutex);
}
EXPORT_SYMBOL_GPL(spec_ctrl_rescan_cpuid);

static ssize_t __enabled_read(struct file *file, char __user *user_buf,
			      size_t count, loff_t *ppos, unsigned int *field)
{
	char buf[32];
	unsigned int len;

	len = sprintf(buf, "%d\n", READ_ONCE(*field));
	return simple_read_from_buffer(user_buf, count, ppos, buf, len);
}

static ssize_t ibrs_enabled_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	return __enabled_read(file, user_buf, count, ppos, &ibrs_enabled);
}

static ssize_t ibrs_enabled_write(struct file *file,
				  const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	char buf[32];
	ssize_t len;
	unsigned int enable;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;

	buf[len] = '\0';
	if (kstrtouint(buf, 0, &enable))
		return -EINVAL;

	if (enable > IBRS_MAX)
		return -EINVAL;

	mutex_lock(&spec_ctrl_mutex);
	if (ibrs_enabled == enable)
		goto out_unlock;

	if (use_ibp_disable) {
		if (enable == IBRS_ENABLED) {
			count = -EINVAL;
			goto out_unlock;
		} else {
			if (enable == IBRS_DISABLED) {
				sync_all_cpus_ibp(true);
				WRITE_ONCE(ibpb_enabled, IBPB_DISABLED);
			} else {
				WARN_ON(enable != IBRS_ENABLED_USER);
				sync_all_cpus_ibp(false);
				WRITE_ONCE(ibpb_enabled, IBPB_ENABLED);
			}
		}
		WRITE_ONCE(ibrs_enabled, enable);
		goto out_unlock;
	}

	if (!cpu_has_spec_ctrl()) {
		count = -ENODEV;
		goto out_unlock;
	}

	if (ibpb_enabled == IBPB_ENABLED_ONLY) {
		count = -EINVAL;
		goto out_unlock;
	}

	if (enable == IBRS_ENABLED) {
		set_spec_ctrl_pcp_ibrs_user(false);
		set_spec_ctrl_pcp_ibrs(true);
	} else {
		set_spec_ctrl_pcp_ibrs(false);
		if (enable == IBRS_DISABLED) {
			set_spec_ctrl_pcp_ibrs_user(false);
			sync_all_cpus_ibrs(false);
		} else {
			WARN_ON(enable != IBRS_ENABLED_USER);
			set_spec_ctrl_pcp_ibrs_user(true);
			sync_all_cpus_ibrs(true);
		}
	}
	WRITE_ONCE(ibrs_enabled, enable);

out_unlock:
	mutex_unlock(&spec_ctrl_mutex);
	return count;
}

static const struct file_operations fops_ibrs_enabled = {
	.read = ibrs_enabled_read,
	.write = ibrs_enabled_write,
	.llseek = default_llseek,
};

static ssize_t ibpb_enabled_read(struct file *file, char __user *user_buf,
				 size_t count, loff_t *ppos)
{
	return __enabled_read(file, user_buf, count, ppos, &ibpb_enabled);
}

static ssize_t ibpb_enabled_write(struct file *file,
				  const char __user *user_buf,
				  size_t count, loff_t *ppos)
{
	char buf[32];
	ssize_t len;
	unsigned int enable;

	len = min(count, sizeof(buf) - 1);
	if (copy_from_user(buf, user_buf, len))
		return -EFAULT;

	buf[len] = '\0';
	if (kstrtouint(buf, 0, &enable))
		return -EINVAL;

	if (enable > IBPB_MAX)
		return -EINVAL;

	mutex_lock(&spec_ctrl_mutex);
	if (ibpb_enabled == enable)
		goto out_unlock;

	if (!boot_cpu_has(X86_FEATURE_IBPB_SUPPORT) || use_ibp_disable) {
		count = -ENODEV;
		goto out_unlock;
	}

	if (enable == IBPB_ENABLED) {
		set_spec_ctrl_pcp_ibpb(true);
		set_spec_ctrl_pcp_only_ibpb(false);
	} else if (enable == IBPB_DISABLED) {
		set_spec_ctrl_pcp_ibpb(false);
		set_spec_ctrl_pcp_only_ibpb(false);
	} else {
		WARN_ON(enable != IBPB_ENABLED_ONLY);
		set_spec_ctrl_pcp_ibpb(true);
		set_spec_ctrl_pcp_only_ibpb(true);

		set_spec_ctrl_pcp_ibrs(false);
		set_spec_ctrl_pcp_ibrs_user(false);
		sync_all_cpus_ibrs(false);
		WRITE_ONCE(ibrs_enabled, IBRS_DISABLED);
	}
	WRITE_ONCE(ibpb_enabled, enable);

out_unlock:
	mutex_unlock(&spec_ctrl_mutex);
	return count;
}

static const struct file_operations fops_ibpb_enabled = {
	.read = ibpb_enabled_read,
	.write = ibpb_enabled_write,
	.llseek = default_llseek,
};

static int __init debugfs_spec_ctrl(void)
{
	debugfs_create_file("ibrs_enabled", S_IRUSR | S_IWUSR,
			    arch_debugfs_dir, NULL, &fops_ibrs_enabled);
	debugfs_create_file("ibpb_enabled", S_IRUSR | S_IWUSR,
			    arch_debugfs_dir, NULL, &fops_ibpb_enabled);
	return 0;
}
late_initcall(debugfs_spec_ctrl);
