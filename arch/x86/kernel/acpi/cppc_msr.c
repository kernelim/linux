// SPDX-License-Identifier: GPL-2.0-only
/*
 * cppc_msr.c:  MSR Interface for CPPC
 * Copyright (c) 2016, Intel Corporation.
 */

#include <acpi/cppc_acpi.h>
#include <asm/msr.h>

/* Refer to drivers/acpi/cppc_acpi.c for the description of functions */

bool cpc_supported_by_cpu(void)
{
	switch (boot_cpu_data.x86_vendor) {
	case X86_VENDOR_AMD:
	case X86_VENDOR_HYGON:
		if (boot_cpu_data.x86 == 0x19 && ((boot_cpu_data.x86_model <= 0x0f) ||
		    (boot_cpu_data.x86_model >= 0x20 && boot_cpu_data.x86_model <= 0x2f)))
			return true;
		else if (boot_cpu_data.x86 == 0x17 &&
			 boot_cpu_data.x86_model >= 0x70 && boot_cpu_data.x86_model <= 0x7f)
			return true;
		return boot_cpu_has(X86_FEATURE_CPPC);
	}
	return false;
}

bool cpc_ffh_supported(void)
{
	return true;
}

int cpc_read_ffh(int cpunum, struct cpc_reg *reg, u64 *val)
{
	int err;

	err = rdmsrl_safe_on_cpu(cpunum, reg->address, val);
	if (!err) {
		u64 mask = GENMASK_ULL(reg->bit_offset + reg->bit_width - 1,
				       reg->bit_offset);

		*val &= mask;
		*val >>= reg->bit_offset;
	}
	return err;
}

int cpc_write_ffh(int cpunum, struct cpc_reg *reg, u64 val)
{
	u64 rd_val;
	int err;

	err = rdmsrl_safe_on_cpu(cpunum, reg->address, &rd_val);
	if (!err) {
		u64 mask = GENMASK_ULL(reg->bit_offset + reg->bit_width - 1,
				       reg->bit_offset);

		val <<= reg->bit_offset;
		val &= mask;
		rd_val &= ~mask;
		rd_val |= val;
		err = wrmsrl_safe_on_cpu(cpunum, reg->address, rd_val);
	}
	return err;
}
