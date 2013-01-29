#ifndef _ASM_S390_CPU_MF_H
#define _ASM_S390_CPU_MF_H

#define CPU_MF_INT_RI_HALTED   (1 <<  5)	/* run-time instr. halted */
#define CPU_MF_INT_RI_BUF_FULL (1 <<  4)	/* run-time instr. program
						   buffer full */

#define CPU_MF_INT_RI_MASK     (CPU_MF_INT_RI_HALTED|CPU_MF_INT_RI_BUF_FULL)

#endif
