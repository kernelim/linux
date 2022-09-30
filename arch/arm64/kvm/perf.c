/*
 * Based on the x86 implementation.
 *
 * Copyright (C) 2012 ARM Ltd.
 * Author: Marc Zyngier <marc.zyngier@arm.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <linux/perf_event.h>
#include <linux/kvm_host.h>

#include <asm/kvm_emulate.h>

static unsigned int kvm_guest_state(void)
{
	struct kvm_vcpu *vcpu = kvm_get_running_vcpu();
	unsigned int state;

	if (!vcpu)
		return 0;

	state = PERF_GUEST_ACTIVE;
	if (!vcpu_mode_priv(vcpu))
		state |= PERF_GUEST_USER;

	return state;
}

static unsigned long kvm_get_guest_ip(void)
{
	struct kvm_vcpu *vcpu = kvm_get_running_vcpu();

	if (WARN_ON_ONCE(!vcpu))
		return 0;

	return *vcpu_pc(vcpu);
}

static struct perf_guest_info_callbacks kvm_guest_cbs = {
	.state		= kvm_guest_state,
	.get_ip		= kvm_get_guest_ip,
};

int kvm_perf_init(void)
{
	return perf_register_guest_info_callbacks(&kvm_guest_cbs);
}

int kvm_perf_teardown(void)
{
	return perf_unregister_guest_info_callbacks(&kvm_guest_cbs);
}
