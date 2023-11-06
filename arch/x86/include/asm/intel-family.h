/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_X86_INTEL_FAMILY_H
#define _ASM_X86_INTEL_FAMILY_H

/*
 * "Big Core" Processors (Branded as Core, Xeon, etc...)
 *
 * While adding a new CPUID for a new microarchitecture, add a new
 * group to keep logically sorted out in chronological order. Within
 * that group keep the CPUID for the variants sorted by model number.
 *
 * The defined symbol names have the following form:
 *	INTEL_FAM6{OPTFAMILY}_{MICROARCH}{OPTDIFF}
 * where:
 * OPTFAMILY	Describes the family of CPUs that this belongs to. Default
 *		is assumed to be "_CORE" (and should be omitted). Other values
 *		currently in use are _ATOM and _XEON_PHI
 * MICROARCH	Is the code name for the micro-architecture for this core.
 *		N.B. Not the platform name.
 * OPTDIFF	If needed, a short string to differentiate by market segment.
 *
 *		Common OPTDIFFs:
 *
 *			- regular client parts
 *		_L	- regular mobile parts
 *		_G	- parts with extra graphics on
 *		_X	- regular server parts
 *		_D	- micro server parts
 *		_N,_P	- other mobile parts
 *		_S	- other client parts
 *
 *		Historical OPTDIFFs:
 *
 *		_EP	- 2 socket server parts
 *		_EX	- 4+ socket server parts
 *
 * The #define line may optionally include a comment including platform or core
 * names. An exception is made for skylake/kabylake where steppings seem to have gotten
 * their own names :-(
 */

/* Wildcard match for FAM6 so X86_MATCH_INTEL_FAM6_MODEL(ANY) works */
#define INTEL_FAM6_ANY			X86_MODEL_ANY

#define INTEL_FAM6_CORE_YONAH		0x0E

#define INTEL_FAM6_CORE2_MEROM		0x0F
#define INTEL_FAM6_CORE2_MEROM_L	0x16
#define INTEL_FAM6_CORE2_PENRYN		0x17
#define INTEL_FAM6_CORE2_DUNNINGTON	0x1D

#define INTEL_FAM6_NEHALEM		0x1E
#define INTEL_FAM6_NEHALEM_G		0x1F /* Auburndale / Havendale */
#define INTEL_FAM6_NEHALEM_EP		0x1A
#define INTEL_FAM6_NEHALEM_EX		0x2E

#define INTEL_FAM6_WESTMERE		0x25
#define INTEL_FAM6_WESTMERE_EP		0x2C
#define INTEL_FAM6_WESTMERE_EX		0x2F

#define INTEL_FAM6_SANDYBRIDGE		0x2A
#define INTEL_FAM6_SANDYBRIDGE_X	0x2D
#define INTEL_FAM6_IVYBRIDGE		0x3A
#define INTEL_FAM6_IVYBRIDGE_X		0x3E

#define INTEL_FAM6_HASWELL		0x3C
#define INTEL_FAM6_HASWELL_X		0x3F
#define INTEL_FAM6_HASWELL_L		0x45
#define INTEL_FAM6_HASWELL_G		0x46

#define INTEL_FAM6_BROADWELL		0x3D
#define INTEL_FAM6_BROADWELL_G		0x47
#define INTEL_FAM6_BROADWELL_X		0x4F
#define INTEL_FAM6_BROADWELL_D		0x56

#define INTEL_FAM6_SKYLAKE_L		0x4E	/* Sky Lake             */
#define INTEL_FAM6_SKYLAKE		0x5E	/* Sky Lake             */
#define INTEL_FAM6_SKYLAKE_X		0x55	/* Sky Lake             */

#define INTEL_FAM6_KABYLAKE_L		0x8E	/* Sky Lake             */
#define INTEL_FAM6_KABYLAKE		0x9E	/* Sky Lake             */

#define INTEL_FAM6_CANNONLAKE_L		0x66	/* Palm Cove */

#define INTEL_FAM6_ICELAKE_X		0x6A	/* Sunny Cove */
#define INTEL_FAM6_ICELAKE_D		0x6C	/* Sunny Cove */
#define INTEL_FAM6_ICELAKE		0x7D	/* Sunny Cove */
#define INTEL_FAM6_ICELAKE_L		0x7E	/* Sunny Cove */

/* "Small Core" Processors (Atom/E-Core) */

#define INTEL_FAM6_ATOM_BONNELL		0x1C /* Diamondville, Pineview */
#define INTEL_FAM6_ATOM_BONNELL_MID	0x26 /* Silverthorne, Lincroft */

#define INTEL_FAM6_ATOM_SALTWELL	0x36 /* Cedarview */
#define INTEL_FAM6_ATOM_SALTWELL_MID	0x27 /* Penwell */
#define INTEL_FAM6_ATOM_SALTWELL_TABLET	0x35 /* Cloverview */

#define INTEL_FAM6_ATOM_SILVERMONT	0x37 /* Bay Trail, Valleyview */
#define INTEL_FAM6_ATOM_SILVERMONT_D	0x4D /* Avaton, Rangely */
#define INTEL_FAM6_ATOM_SILVERMONT_MID	0x4A /* Merriefield */

#define INTEL_FAM6_ATOM_AIRMONT		0x4C /* Cherry Trail, Braswell */
#define INTEL_FAM6_ATOM_AIRMONT_MID	0x5A /* Moorefield */

#define INTEL_FAM6_ATOM_GOLDMONT	0x5C /* Apollo Lake */
#define INTEL_FAM6_ATOM_GOLDMONT_D	0x5F /* Denverton */
#define INTEL_FAM6_ATOM_GOLDMONT_PLUS	0x7A /* Gemini Lake */

#define INTEL_FAM6_ATOM_TREMONT_D	0x86 /* Jacobsville */

/* Xeon Phi */

#define INTEL_FAM6_XEON_PHI_KNL		0x57 /* Knights Landing */
#define INTEL_FAM6_XEON_PHI_KNM		0x85 /* Knights Mill */

/* Intel family compatibility names */
#define INTEL_FAM6_HASWELL_CORE		INTEL_FAM6_HASWELL
#define INTEL_FAM6_HASWELL_ULT		INTEL_FAM6_HASWELL_L
#define INTEL_FAM6_HASWELL_GT3E		INTEL_FAM6_HASWELL_G
#define INTEL_FAM6_BROADWELL_CORE	INTEL_FAM6_BROADWELL
#define INTEL_FAM6_BROADWELL_GT3E	INTEL_FAM6_BROADWELL_G
#define INTEL_FAM6_BROADWELL_XEON_D	INTEL_FAM6_BROADWELL_D
#define INTEL_FAM6_SKYLAKE_MOBILE	INTEL_FAM6_SKYLAKE_L
#define INTEL_FAM6_SKYLAKE_DESKTOP	INTEL_FAM6_SKYLAKE
#define INTEL_FAM6_CANNONLAKE_MOBILE	INTEL_FAM6_CANNONLAKE_L
#define INTEL_FAM6_KABYLAKE_MOBILE	INTEL_FAM6_KABYLAKE_L
#define INTEL_FAM6_KABYLAKE_DESKTOP	INTEL_FAM6_KABYLAKE
#define INTEL_FAM6_ICELAKE_XEON_D	INTEL_FAM6_ICELAKE_D
#define INTEL_FAM6_ICELAKE_DESKTOP	INTEL_FAM6_ICELAKE
#define INTEL_FAM6_ICELAKE_MOBILE	INTEL_FAM6_ICELAKE_L
#define INTEL_FAM6_ATOM_SILVERMONT_X	INTEL_FAM6_ATOM_SILVERMONT_D
#define INTEL_FAM6_ATOM_GOLDMONT_X	INTEL_FAM6_ATOM_GOLDMONT_D
#define INTEL_FAM6_ATOM_TREMONT_X	INTEL_FAM6_ATOM_TREMONT_D

#endif /* _ASM_X86_INTEL_FAMILY_H */
