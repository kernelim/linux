// SPDX-License-Identifier: GPL-2.0-only
/*
 * Copyright (C) 2015 - ARM Ltd
 * Author: Marc Zyngier <marc.zyngier@arm.com>
 */

#include <hyp/debug-sr.h>

#include <linux/compiler.h>
#include <linux/kvm_host.h>

#include <asm/debug-monitors.h>
#include <asm/kvm_asm.h>
#include <asm/kvm_hyp.h>
#include <asm/kvm_mmu.h>

static void __debug_save_spe(void)
{
	u64 *pmscr_el1, *pmblimitr_el1;

	pmscr_el1 = host_data_ptr(host_debug_state.pmscr_el1);
	pmblimitr_el1 = host_data_ptr(host_debug_state.pmblimitr_el1);

	/*
	 * At this point, we know that this CPU implements
	 * SPE and is available to the host.
	 * Check if the host is actually using it ?
	 */
	*pmblimitr_el1 = read_sysreg_s(SYS_PMBLIMITR_EL1);
	if (!(*pmblimitr_el1 & BIT(PMBLIMITR_EL1_E_SHIFT)))
		return;

	/* Yes; save the control register and disable data generation */
	*pmscr_el1 = read_sysreg_el1(SYS_PMSCR);
	write_sysreg_el1(0, SYS_PMSCR);
	isb();

	/* Now drain all buffered data to memory */
	psb_csync();
	dsb(nsh);

	/* And disable the profiling buffer */
	write_sysreg_s(0, SYS_PMBLIMITR_EL1);
	isb();
}

static void __debug_restore_spe(void)
{
	u64 pmblimitr_el1 = *host_data_ptr(host_debug_state.pmblimitr_el1);

	if (!(pmblimitr_el1 & BIT(PMBLIMITR_EL1_E_SHIFT)))
		return;

	/* The host page table is installed, but not yet synchronised */
	isb();

	/* Re-enable the profiling buffer. */
	write_sysreg_s(pmblimitr_el1, SYS_PMBLIMITR_EL1);
	isb();

	/* Re-enable data generation */
	write_sysreg_el1(*host_data_ptr(host_debug_state.pmscr_el1), SYS_PMSCR);
}

static void __debug_save_trace(void)
{
	u64 *trfcr_el1, *trblimitr_el1;

	trfcr_el1 = host_data_ptr(host_debug_state.trfcr_el1);
	trblimitr_el1 = host_data_ptr(host_debug_state.trblimitr_el1);

	*trblimitr_el1 = read_sysreg_s(SYS_TRBLIMITR_EL1);
	*trfcr_el1 = 0;

	/* Check if the TRBE is enabled */
	if (!(read_sysreg_s(SYS_TRBLIMITR_EL1) & TRBLIMITR_EL1_E))
		return;
	/*
	 * Prohibit trace generation while we are in guest.
	 * Since access to TRFCR_EL1 is trapped, the guest can't
	 * modify the filtering set by the host.
	 */
	*trfcr_el1 = read_sysreg_el1(SYS_TRFCR);
	write_sysreg_el1(0, SYS_TRFCR);
	isb();
	/* Drain the trace buffer to memory */
	tsb_csync();
	dsb(nsh);

	/*
	 * With no more trace being generated, we can disable the
	 * Trace Buffer Unit.
	 */
	write_sysreg_s(0, SYS_TRBLIMITR_EL1);
	if (cpus_have_final_cap(ARM64_WORKAROUND_2064142)) {
		/*
		 * Some CPUs are so good, we have to drain 'em
		 * twice.
		 */
		tsb_csync();
		dsb(nsh);
	}

	/*
	 * Ensure that the Trace Buffer Unit is disabled before
	 * we start mucking with the stage-2 and trap
	 * configuration.
	 */
	isb();
}

static void __debug_restore_trace(void)
{
	uint64_t trfcr_el1 = *host_data_ptr(host_debug_state.trfcr_el1);
	uint64_t trblimitr_el1 = *host_data_ptr(host_debug_state.trblimitr_el1);

	if (!trfcr_el1)
		return;

	if (trblimitr_el1 & TRBLIMITR_EL1_E) {
		/* Re-enable the Trace Buffer Unit for the host. */
		write_sysreg_s(trblimitr_el1, SYS_TRBLIMITR_EL1);
		isb();
		if (cpus_have_final_cap(ARM64_WORKAROUND_2038923)) {
			/*
			 * Make sure the unit is re-enabled before we
			 * poke TRFCR.
			 */
			isb();
		}
	}

	/* Restore trace filter controls */
	write_sysreg_el1(trfcr_el1, SYS_TRFCR);
}

void __debug_save_host_buffers_nvhe(struct kvm_vcpu *vcpu)
{
	/* Disable and flush SPE data generation */
	if (vcpu_get_flag(vcpu, DEBUG_STATE_SAVE_SPE))
		__debug_save_spe();
	/* Disable and flush Self-Hosted Trace generation */
	if (vcpu_get_flag(vcpu, DEBUG_STATE_SAVE_TRBE))
		__debug_save_trace();
}

void __debug_switch_to_guest(struct kvm_vcpu *vcpu)
{
	__debug_switch_to_guest_common(vcpu);
}

void __debug_restore_host_buffers_nvhe(struct kvm_vcpu *vcpu)
{
	if (vcpu_get_flag(vcpu, DEBUG_STATE_SAVE_SPE))
		__debug_restore_spe();
	if (vcpu_get_flag(vcpu, DEBUG_STATE_SAVE_TRBE))
		__debug_restore_trace();
}

void __debug_switch_to_host(struct kvm_vcpu *vcpu)
{
	__debug_switch_to_host_common(vcpu);
}

u64 __kvm_get_mdcr_el2(void)
{
	return read_sysreg(mdcr_el2);
}
