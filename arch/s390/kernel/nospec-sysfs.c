// SPDX-License-Identifier: GPL-2.0
#include <linux/device.h>
#include <linux/cpu.h>
#include <asm/nospec-branch.h>

ssize_t cpu_show_spectre_v1(struct sysdev_class *class, char *buf)
{
	return sprintf(buf, "Mitigation: __user pointer sanitization\n");
}

ssize_t cpu_show_spectre_v2(struct sysdev_class *class, char *buf)
{
	if (MACHINE_HAS_ETOKEN)
		return sprintf(buf, "Mitigation: etokens\n");
	if (IS_ENABLED(CC_USING_EXPOLINE) && !nospec_disable)
		return sprintf(buf, "Mitigation: execute trampolines\n");
	if (nobp_flag)
		return sprintf(buf, "Mitigation: limited branch prediction\n");
	return sprintf(buf, "Vulnerable\n");
}
