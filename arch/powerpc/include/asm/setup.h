#ifndef _ASM_POWERPC_SETUP_H
#define _ASM_POWERPC_SETUP_H

#include <asm-generic/setup.h>

#ifndef __ASSEMBLY__

void rfi_flush_enable(bool enable);

/* These are bit flags */
enum stf_barrier_type {
	STF_BARRIER_NONE	= 0x1,
	STF_BARRIER_FALLBACK	= 0x2,
	STF_BARRIER_EIEIO	= 0x4,
	STF_BARRIER_SYNC_ORI	= 0x8,
};

void setup_stf_barrier(void);
void do_stf_barrier_fixups(enum stf_barrier_type types);

enum l1d_flush_type {
	L1D_FLUSH_NONE		= 0x1,
	L1D_FLUSH_FALLBACK	= 0x2,
	L1D_FLUSH_ORI		= 0x4,
	L1D_FLUSH_MTTRIG	= 0x8,
};

void setup_rfi_flush(enum l1d_flush_type, bool enable);
void do_rfi_flush_fixups(enum l1d_flush_type types);
#endif

#endif	/* _ASM_POWERPC_SETUP_H */
