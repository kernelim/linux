#ifndef __ASM_S390_NOBP_H
#define __ASM_S390_NOBP_H

#ifdef __ASSEMBLY__

.macro BPON
	.pushsection .altinstr_replacement, "ax"
662:	.long	0xb2e8d000
	.popsection
663:	.long	0x47000000
	.pushsection .altinstructions, "a"
        .long 663b - .
	.long 662b - .
	.word 82
	.byte 4
	.byte 4
	.popsection
.endm

#endif	/* __ASSEMBLY__ */
#endif	/* __ASM_S390_NOBP_H */
