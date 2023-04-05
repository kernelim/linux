/*
 * AMD Memory Encryption Support
 *
 * Copyright (C) 2017 Advanced Micro Devices, Inc.
 *
 * Author: Tom Lendacky <thomas.lendacky@amd.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 */

#include <linux/linkage.h>

#include <asm/processor-flags.h>
#include <asm/msr.h>
#include <asm/asm-offsets.h>

	.text
	.code32
SYM_FUNC_START(get_sev_encryption_bit)
	xor	%eax, %eax

#ifdef CONFIG_AMD_MEM_ENCRYPT
	push	%ebx
	push	%ecx
	push	%edx

	movl	$0x80000000, %eax	/* CPUID to check the highest leaf */
	cpuid
	cmpl	$0x8000001f, %eax	/* See if 0x8000001f is available */
	jb	.Lno_sev

	/*
	 * Check for the SEV feature:
	 *   CPUID Fn8000_001F[EAX] - Bit 1
	 *   CPUID Fn8000_001F[EBX] - Bits 5:0
	 *     Pagetable bit position used to indicate encryption
	 */
	movl	$0x8000001f, %eax
	cpuid
	bt	$1, %eax		/* Check if SEV is available */
	jnc	.Lno_sev

	movl	$MSR_AMD64_SEV, %ecx	/* Read the SEV MSR */
	rdmsr
	bt	$MSR_AMD64_SEV_ENABLED_BIT, %eax	/* Check if SEV is active */
	jnc	.Lno_sev

	movl	%ebx, %eax
	andl	$0x3f, %eax		/* Return the encryption bit location */
	jmp	.Lsev_exit

.Lno_sev:
	xor	%eax, %eax

.Lsev_exit:
	pop	%edx
	pop	%ecx
	pop	%ebx

#endif	/* CONFIG_AMD_MEM_ENCRYPT */

	ret
SYM_FUNC_END(get_sev_encryption_bit)

	.code64

#include "../../kernel/sev_verify_cbit.S"

	.data

#ifdef CONFIG_AMD_MEM_ENCRYPT
	.balign	8
GLOBAL(sme_me_mask)
	.quad	0
SYM_DATA(sev_status,		.quad 0)
SYM_DATA(sev_check_data,	.quad 0)
#endif
