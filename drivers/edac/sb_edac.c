/* Intel Sandy Bridge -EN/-EP/-EX Memory Controller kernel module
 *
 * This driver supports the memory controllers found on the Intel
 * processor family Sandy Bridge.
 *
 * This file may be distributed under the terms of the
 * GNU General Public License version 2 only.
 *
 * Copyright (c) 2011 by:
 *	 Mauro Carvalho Chehab <mchehab@redhat.com>
 */

#include <linux/module.h>
#include <linux/init.h>
#include <linux/pci.h>
#include <linux/pci_ids.h>
#include <linux/slab.h>
#include <linux/delay.h>
#include <linux/edac.h>
#include <linux/mmzone.h>
#include <linux/smp.h>
#include <linux/bitmap.h>
#include <linux/math64.h>
#include <asm/processor.h>
#include <asm/mce.h>

#include "edac_core.h"

/* Static vars */
static LIST_HEAD(sbridge_edac_list);
static DEFINE_MUTEX(sbridge_edac_lock);
static int probed;

/*
 * Alter this version for the module when modifications are made
 */
#define SBRIDGE_REVISION    " Ver: 1.1.0 "
#define EDAC_MOD_STR      "sbridge_edac"

/*
 * Debug macros
 */
#define sbridge_printk(level, fmt, arg...)			\
	edac_printk(level, "sbridge", fmt, ##arg)

#define sbridge_mc_printk(mci, level, fmt, arg...)		\
	edac_mc_chipset_printk(mci, level, "sbridge", fmt, ##arg)

/*
 * Get a bit field at register value <v>, from bit <lo> to bit <hi>
 */
#define GET_BITFIELD(v, lo, hi)	\
	(((v) & GENMASK_ULL(hi, lo)) >> (lo))

/*
 * sbridge Memory Controller Registers
 */

/*
 * FIXME: For now, let's order by device function, as it makes
 * easier for driver's development proccess. This table should be
 * moved to pci_id.h when submitted upstream
 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_SAD0	0x3cf4	/* 12.6 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_SAD1	0x3cf6	/* 12.7 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_BR		0x3cf5	/* 13.6 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_HA0	0x3ca0	/* 14.0 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TA	0x3ca8	/* 15.0 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_RAS	0x3c71	/* 15.1 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD0	0x3caa	/* 15.2 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD1	0x3cab	/* 15.3 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD2	0x3cac	/* 15.4 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD3	0x3cad	/* 15.5 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_DDRIO	0x3cb8	/* 17.0 */

	/*
	 * Currently, unused, but will be needed in the future
	 * implementations, as they hold the error counters
	 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_ERR0	0x3c72	/* 16.2 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_ERR1	0x3c73	/* 16.3 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_ERR2	0x3c76	/* 16.6 */
#define PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_ERR3	0x3c77	/* 16.7 */

/* Devices 12 Function 6, Offsets 0x80 to 0xcc */
static const u32 sbridge_dram_rule[] = {
	0x80, 0x88, 0x90, 0x98, 0xa0,
	0xa8, 0xb0, 0xb8, 0xc0, 0xc8,
};

static const u32 ibridge_dram_rule[] = {
	0x60, 0x68, 0x70, 0x78, 0x80,
	0x88, 0x90, 0x98, 0xa0,	0xa8,
	0xb0, 0xb8, 0xc0, 0xc8, 0xd0,
	0xd8, 0xe0, 0xe8, 0xf0, 0xf8,
};

#define SAD_LIMIT(reg)		((GET_BITFIELD(reg, 6, 25) << 26) | 0x3ffffff)
#define DRAM_ATTR(reg)		GET_BITFIELD(reg, 2,  3)
#define INTERLEAVE_MODE(reg)	GET_BITFIELD(reg, 1,  1)
#define DRAM_RULE_ENABLE(reg)	GET_BITFIELD(reg, 0,  0)
#define A7MODE(reg)		GET_BITFIELD(reg, 26, 26)

static char *get_dram_attr(u32 reg)
{
	switch(DRAM_ATTR(reg)) {
		case 0:
			return "DRAM";
		case 1:
			return "MMCFG";
		case 2:
			return "NXM";
		default:
			return "unknown";
	}
}

static const u32 sbridge_interleave_list[] = {
	0x84, 0x8c, 0x94, 0x9c, 0xa4,
	0xac, 0xb4, 0xbc, 0xc4, 0xcc,
};

static const u32 ibridge_interleave_list[] = {
	0x64, 0x6c, 0x74, 0x7c, 0x84,
	0x8c, 0x94, 0x9c, 0xa4, 0xac,
	0xb4, 0xbc, 0xc4, 0xcc, 0xd4,
	0xdc, 0xe4, 0xec, 0xf4, 0xfc,
};

struct interleave_pkg {
	unsigned char start;
	unsigned char end;
};

static const struct interleave_pkg sbridge_interleave_pkg[] = {
	{ 0, 2 },
	{ 3, 5 },
	{ 8, 10 },
	{ 11, 13 },
	{ 16, 18 },
	{ 19, 21 },
	{ 24, 26 },
	{ 27, 29 },
};

static const struct interleave_pkg ibridge_interleave_pkg[] = {
	{ 0, 3 },
	{ 4, 7 },
	{ 8, 11 },
	{ 12, 15 },
	{ 16, 19 },
	{ 20, 23 },
	{ 24, 27 },
	{ 28, 31 },
};

static inline int sad_pkg(const struct interleave_pkg *table, u32 reg,
			  int interleave)
{
	return GET_BITFIELD(reg, table[interleave].start,
			    table[interleave].end);
}

/* Devices 12 Function 7 */

#define TOLM		0x80
#define	TOHM		0x84
#define HASWELL_TOHM_0	0xd4
#define HASWELL_TOHM_1	0xd8

#define GET_TOLM(reg)		((GET_BITFIELD(reg, 0,  3) << 28) | 0x3ffffff)
#define GET_TOHM(reg)		((GET_BITFIELD(reg, 0, 20) << 25) | 0x3ffffff)

/* Device 13 Function 6 */

#define SAD_TARGET	0xf0

#define SOURCE_ID(reg)		GET_BITFIELD(reg, 9, 11)

#define SAD_CONTROL	0xf4

/* Device 14 function 0 */

static const u32 tad_dram_rule[] = {
	0x40, 0x44, 0x48, 0x4c,
	0x50, 0x54, 0x58, 0x5c,
	0x60, 0x64, 0x68, 0x6c,
};
#define MAX_TAD	ARRAY_SIZE(tad_dram_rule)

#define TAD_LIMIT(reg)		((GET_BITFIELD(reg, 12, 31) << 26) | 0x3ffffff)
#define TAD_SOCK(reg)		GET_BITFIELD(reg, 10, 11)
#define TAD_CH(reg)		GET_BITFIELD(reg,  8,  9)
#define TAD_TGT3(reg)		GET_BITFIELD(reg,  6,  7)
#define TAD_TGT2(reg)		GET_BITFIELD(reg,  4,  5)
#define TAD_TGT1(reg)		GET_BITFIELD(reg,  2,  3)
#define TAD_TGT0(reg)		GET_BITFIELD(reg,  0,  1)

/* Device 15, function 0 */

#define MCMTR			0x7c

#define IS_ECC_ENABLED(mcmtr)		GET_BITFIELD(mcmtr, 2, 2)
#define IS_LOCKSTEP_ENABLED(mcmtr)	GET_BITFIELD(mcmtr, 1, 1)
#define IS_CLOSE_PG(mcmtr)		GET_BITFIELD(mcmtr, 0, 0)

/* Device 15, function 1 */

#define RASENABLES		0xac
#define IS_MIRROR_ENABLED(reg)		GET_BITFIELD(reg, 0, 0)

/* Device 15, functions 2-5 */

static const int mtr_regs[] = {
	0x80, 0x84, 0x88,
};

#define RANK_DISABLE(mtr)		GET_BITFIELD(mtr, 16, 19)
#define IS_DIMM_PRESENT(mtr)		GET_BITFIELD(mtr, 14, 14)
#define RANK_CNT_BITS(mtr)		GET_BITFIELD(mtr, 12, 13)
#define RANK_WIDTH_BITS(mtr)		GET_BITFIELD(mtr, 2, 4)
#define COL_WIDTH_BITS(mtr)		GET_BITFIELD(mtr, 0, 1)

static const u32 tad_ch_nilv_offset[] = {
	0x90, 0x94, 0x98, 0x9c,
	0xa0, 0xa4, 0xa8, 0xac,
	0xb0, 0xb4, 0xb8, 0xbc,
};
#define CHN_IDX_OFFSET(reg)		GET_BITFIELD(reg, 28, 29)
#define TAD_OFFSET(reg)			(GET_BITFIELD(reg,  6, 25) << 26)

static const u32 rir_way_limit[] = {
	0x108, 0x10c, 0x110, 0x114, 0x118,
};
#define MAX_RIR_RANGES ARRAY_SIZE(rir_way_limit)

#define IS_RIR_VALID(reg)	GET_BITFIELD(reg, 31, 31)
#define RIR_WAY(reg)		GET_BITFIELD(reg, 28, 29)

#define MAX_RIR_WAY	8

static const u32 rir_offset[MAX_RIR_RANGES][MAX_RIR_WAY] = {
	{ 0x120, 0x124, 0x128, 0x12c, 0x130, 0x134, 0x138, 0x13c },
	{ 0x140, 0x144, 0x148, 0x14c, 0x150, 0x154, 0x158, 0x15c },
	{ 0x160, 0x164, 0x168, 0x16c, 0x170, 0x174, 0x178, 0x17c },
	{ 0x180, 0x184, 0x188, 0x18c, 0x190, 0x194, 0x198, 0x19c },
	{ 0x1a0, 0x1a4, 0x1a8, 0x1ac, 0x1b0, 0x1b4, 0x1b8, 0x1bc },
};

#define RIR_RNK_TGT(reg)		GET_BITFIELD(reg, 16, 19)
#define RIR_OFFSET(reg)		GET_BITFIELD(reg,  2, 14)

/* Device 16, functions 2-7 */

/*
 * FIXME: Implement the error count reads directly
 */

static const u32 correrrcnt[] = {
	0x104, 0x108, 0x10c, 0x110,
};

#define RANK_ODD_OV(reg)		GET_BITFIELD(reg, 31, 31)
#define RANK_ODD_ERR_CNT(reg)		GET_BITFIELD(reg, 16, 30)
#define RANK_EVEN_OV(reg)		GET_BITFIELD(reg, 15, 15)
#define RANK_EVEN_ERR_CNT(reg)		GET_BITFIELD(reg,  0, 14)

static const u32 correrrthrsld[] = {
	0x11c, 0x120, 0x124, 0x128,
};

#define RANK_ODD_ERR_THRSLD(reg)	GET_BITFIELD(reg, 16, 30)
#define RANK_EVEN_ERR_THRSLD(reg)	GET_BITFIELD(reg,  0, 14)


/* Device 17, function 0 */

#define SB_RANK_CFG_A		0x0328

#define IB_RANK_CFG_A		0x0320

/*
 * sbridge structs
 */

#define NUM_CHANNELS	4
#define MAX_DIMMS	3		/* Max DIMMS per channel */

enum type {
	SANDY_BRIDGE,
	IVY_BRIDGE,
	HASWELL,
};

struct sbridge_pvt;
struct sbridge_info {
	enum type	type;
	u32		mcmtr;
	u32		rankcfgr;
	u64		(*get_tolm)(struct sbridge_pvt *pvt);
	u64		(*get_tohm)(struct sbridge_pvt *pvt);
	u64		(*rir_limit)(u32 reg);
	const u32	*dram_rule;
	const u32	*interleave_list;
	const struct interleave_pkg *interleave_pkg;
	u8		max_sad;
	u8		max_interleave;
	u8		(*get_node_id)(struct sbridge_pvt *pvt);
	enum mem_type	(*get_memory_type)(struct sbridge_pvt *pvt);
	struct pci_dev	*pci_vtd;
};

struct sbridge_channel {
	u32		ranks;
	u32		dimms;
};

struct pci_id_descr {
	int 			dev_id;
	int			optional;
};

struct pci_id_table {
	const struct pci_id_descr	*descr;
	int				n_devs;
};

struct sbridge_dev {
	struct list_head	list;
	u8			bus, mc;
	u8			node_id, source_id;
	struct pci_dev		**pdev;
	int			n_devs;
	struct mem_ctl_info	*mci;
};

struct sbridge_pvt {
	struct pci_dev		*pci_ta, *pci_ddrio, *pci_ras;
	struct pci_dev		*pci_sad0, *pci_sad1;
	struct pci_dev		*pci_ha0, *pci_ha1;
	struct pci_dev		*pci_br0, *pci_br1;
	struct pci_dev		*pci_ha1_ta;
	struct pci_dev		*pci_tad[NUM_CHANNELS];

	struct sbridge_dev	*sbridge_dev;

	struct sbridge_info	info;
	struct sbridge_channel	channel[NUM_CHANNELS];

	int 			csrow_map[NUM_CHANNELS][MAX_DIMMS];

	/* Memory type detection */
	bool			is_mirrored, is_lockstep, is_close_pg;

	/* Fifo double buffers */
	struct mce		mce_entry[MCE_LOG_LEN];
	struct mce		mce_outentry[MCE_LOG_LEN];

	/* Fifo in/out counters */
	unsigned		mce_in, mce_out;

	/* Count indicator to show errors not got */
	unsigned		mce_overrun;

	/* Memory description */
	u64			tolm, tohm;
};

#define PCI_DESCR(device_id, opt)	\
	.dev_id = (device_id),		\
	.optional = opt

static const struct pci_id_descr pci_dev_descr_sbridge[] = {
		/* Processor Home Agent */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_HA0, 0)	},

		/* Memory controller */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TA, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_RAS, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD0, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD1, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD2, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD3, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_DDRIO, 1)	},

		/* System Address Decoder */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_SAD0, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_SAD1, 0)	},

		/* Broadcast Registers */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_SBRIDGE_BR, 0)		},
};

#define PCI_ID_TABLE_ENTRY(A) { .descr=A, .n_devs = ARRAY_SIZE(A) }
static const struct pci_id_table pci_dev_descr_sbridge_table[] = {
	PCI_ID_TABLE_ENTRY(pci_dev_descr_sbridge),
	{0,}			/* 0 terminated list. */
};

/* This changes depending if 1HA or 2HA:
 * 1HA:
 *	0x0eb8 (17.0) is DDRIO0
 * 2HA:
 *	0x0ebc (17.4) is DDRIO0
 */
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_1HA_DDRIO0	0x0eb8
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_2HA_DDRIO0	0x0ebc

/* pci ids */
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0		0x0ea0
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TA		0x0ea8
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_RAS		0x0e71
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD0	0x0eaa
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD1	0x0eab
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD2	0x0eac
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD3	0x0ead
#define PCI_DEVICE_ID_INTEL_IBRIDGE_SAD			0x0ec8
#define PCI_DEVICE_ID_INTEL_IBRIDGE_BR0			0x0ec9
#define PCI_DEVICE_ID_INTEL_IBRIDGE_BR1			0x0eca
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1		0x0e60
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TA		0x0e68
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_RAS		0x0e79
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD0	0x0e6a
#define PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD1	0x0e6b

static const struct pci_id_descr pci_dev_descr_ibridge[] = {
		/* Processor Home Agent */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0, 0)		},

		/* Memory controller */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TA, 0)		},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_RAS, 0)		},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD0, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD1, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD2, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD3, 0)	},

		/* System Address Decoder */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_SAD, 0)			},

		/* Broadcast Registers */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_BR0, 1)			},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_BR1, 0)			},

		/* Optional, mode 2HA */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1, 1)		},
#if 0
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TA, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_RAS, 1)	},
#endif
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD0, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD1, 1)	},

	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_1HA_DDRIO0, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_2HA_DDRIO0, 1)	},
};

static const struct pci_id_table pci_dev_descr_ibridge_table[] = {
	PCI_ID_TABLE_ENTRY(pci_dev_descr_ibridge),
	{0,}			/* 0 terminated list. */
};

/* Haswell support */
/* EN processor:
 *	- 1 IMC
 *	- 3 DDR3 channels, 2 DPC per channel
 * EP processor:
 *	- 1 or 2 IMC
 *	- 4 DDR4 channels, 3 DPC per channel
 * EP 4S processor:
 *	- 2 IMC
 *	- 4 DDR4 channels, 3 DPC per channel
 * EX processor:
 *	- 2 IMC
 *	- each IMC interfaces with a SMI 2 channel
 *	- each SMI channel interfaces with a scalable memory buffer
 *	- each scalable memory buffer supports 2 DDR3 channels, 3 DPC
 */
#define HASWELL_DDRCRCLKCONTROLS 0xa10
#define HASWELL_HASYSDEFEATURE2 0x84
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_VTD_MISC 0x2f28
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0	0x2fa0
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1	0x2f60
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TA	0x2fa8
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_THERMAL 0x2f71
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TA	0x2f68
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_THERMAL 0x2f79
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_CBO_SAD0 0x2ffc
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_CBO_SAD1 0x2ffd
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD0 0x2faa
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD1 0x2fab
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD2 0x2fac
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD3 0x2fad
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD0 0x2f6a
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD1 0x2f6b
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD2 0x2f6c
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD3 0x2f6d
#define PCI_DEVICE_ID_INTEL_HASWELL_IMC_DDRIO0 0x2fbd
static const struct pci_id_descr pci_dev_descr_haswell[] = {
	/* first item must be the HA */
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0, 0)		},

	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_CBO_SAD0, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_CBO_SAD1, 0)	},

	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1, 1)		},

	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TA, 0)		},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_THERMAL, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD0, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD1, 0)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD2, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD3, 1)	},

	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_DDRIO0, 1)		},

	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TA, 1)		},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_THERMAL, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD0, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD1, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD2, 1)	},
	{ PCI_DESCR(PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD3, 1)	},
};

static const struct pci_id_table pci_dev_descr_haswell_table[] = {
	PCI_ID_TABLE_ENTRY(pci_dev_descr_haswell),
	{0,}			/* 0 terminated list. */
};

/*
 *	pci_device_id	table for which devices we are looking for
 */
static const struct pci_device_id sbridge_pci_tbl[] __devinitdata = {
	{PCI_DEVICE(PCI_VENDOR_ID_INTEL, PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TA)},
	{PCI_DEVICE(PCI_VENDOR_ID_INTEL, PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TA)},
	{PCI_DEVICE(PCI_VENDOR_ID_INTEL, PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0)},
	{0,}			/* 0 terminated list. */
};


/****************************************************************************
			Anciliary status routines
 ****************************************************************************/

static inline int numrank(enum type type, u32 mtr)
{
	int ranks = (1 << RANK_CNT_BITS(mtr));
	int max = 4;

	if (type == HASWELL)
		max = 8;

	if (ranks > max) {
		debugf0("Invalid number of ranks: %d (max = %i) raw value = %x (%04x)\n",
			 ranks, max, (unsigned int)RANK_CNT_BITS(mtr), mtr);
		return -EINVAL;
	}

	return ranks;
}

static inline int numrow(u32 mtr)
{
	int rows = (RANK_WIDTH_BITS(mtr) + 12);

	if (rows < 13 || rows > 18) {
		debugf0("Invalid number of rows: %d (should be between 14 and 17) raw value = %x (%04x)",
			rows, (unsigned int)RANK_WIDTH_BITS(mtr), mtr);
		return -EINVAL;
	}

	return 1 << rows;
}

static inline int numcol(u32 mtr)
{
	int cols = (COL_WIDTH_BITS(mtr) + 10);

	if (cols > 12) {
		debugf0("Invalid number of cols: %d (max = 4) raw value = %x (%04x)",
			cols, (unsigned int)COL_WIDTH_BITS(mtr), mtr);
		return -EINVAL;
	}

	return 1 << cols;
}

static struct sbridge_dev *get_sbridge_dev(u8 bus)
{
	struct sbridge_dev *sbridge_dev;

	list_for_each_entry(sbridge_dev, &sbridge_edac_list, list) {
		if (sbridge_dev->bus == bus)
			return sbridge_dev;
	}

	return NULL;
}

static struct sbridge_dev *alloc_sbridge_dev(u8 bus,
					   const struct pci_id_table *table)
{
	struct sbridge_dev *sbridge_dev;

	sbridge_dev = kzalloc(sizeof(*sbridge_dev), GFP_KERNEL);
	if (!sbridge_dev)
		return NULL;

	sbridge_dev->pdev = kzalloc(sizeof(*sbridge_dev->pdev) * table->n_devs,
				   GFP_KERNEL);
	if (!sbridge_dev->pdev) {
		kfree(sbridge_dev);
		return NULL;
	}

	sbridge_dev->bus = bus;
	sbridge_dev->n_devs = table->n_devs;
	list_add_tail(&sbridge_dev->list, &sbridge_edac_list);

	return sbridge_dev;
}

static void free_sbridge_dev(struct sbridge_dev *sbridge_dev)
{
	list_del(&sbridge_dev->list);
	kfree(sbridge_dev->pdev);
	kfree(sbridge_dev);
}

static u64 sbridge_get_tolm(struct sbridge_pvt *pvt)
{
	u32 reg;

	/* Address range is 32:28 */
	pci_read_config_dword(pvt->pci_sad1, TOLM, &reg);
	return GET_TOLM(reg);
}

static u64 sbridge_get_tohm(struct sbridge_pvt *pvt)
{
	u32 reg;

	pci_read_config_dword(pvt->pci_sad1, TOHM, &reg);
	return GET_TOHM(reg);
}

static u64 ibridge_get_tolm(struct sbridge_pvt *pvt)
{
	u32 reg;

	pci_read_config_dword(pvt->pci_br1, TOLM, &reg);

	return GET_TOLM(reg);
}

static u64 ibridge_get_tohm(struct sbridge_pvt *pvt)
{
	u32 reg;

	pci_read_config_dword(pvt->pci_br1, TOHM, &reg);

	return GET_TOHM(reg);
}

static u64 rir_limit(u32 reg)
{
	return ((u64)GET_BITFIELD(reg,  1, 10) << 29) | 0x1fffffff;
}

static enum mem_type get_memory_type(struct sbridge_pvt *pvt)
{
	u32 reg;
	enum mem_type mtype;

	if (pvt->pci_ddrio) {
		pci_read_config_dword(pvt->pci_ddrio, pvt->info.rankcfgr,
				      &reg);
		if (GET_BITFIELD(reg, 11, 11))
			/* FIXME: Can also be LRDIMM */
			mtype = MEM_RDDR3;
		else
			mtype = MEM_DDR3;
	} else
		mtype = MEM_UNKNOWN;

	return mtype;
}

static enum mem_type haswell_get_memory_type(struct sbridge_pvt *pvt)
{
	u32 reg;
	bool registered = false;
	enum mem_type mtype = MEM_UNKNOWN;

	if (!pvt->pci_ddrio)
		goto out;

	pci_read_config_dword(pvt->pci_ddrio,
			      HASWELL_DDRCRCLKCONTROLS, &reg);
	/* Is_Rdimm */
	if (GET_BITFIELD(reg, 16, 16))
		registered = true;

	pci_read_config_dword(pvt->pci_ta, MCMTR, &reg);
	if (GET_BITFIELD(reg, 14, 14)) {
		if (registered)
			mtype = MEM_RDDR4;
		else
			mtype = MEM_DDR4;
	} else {
		if (registered)
			mtype = MEM_RDDR3;
		else
			mtype = MEM_DDR3;
	}

out:
	return mtype;
}

static u8 get_node_id(struct sbridge_pvt *pvt)
{
	u32 reg;
	pci_read_config_dword(pvt->pci_br0, SAD_CONTROL, &reg);
	return GET_BITFIELD(reg, 0, 2);
}

static u8 haswell_get_node_id(struct sbridge_pvt *pvt)
{
	u32 reg;
	pci_read_config_dword(pvt->pci_sad1, SAD_CONTROL, &reg);
	return GET_BITFIELD(reg, 0, 3);
}

static u64 haswell_get_tolm(struct sbridge_pvt *pvt)
{
	u32 reg;
	pci_read_config_dword(pvt->info.pci_vtd, TOLM, &reg);
	return (GET_BITFIELD(reg, 26, 31) << 26) | 0x1ffffff;
}

static u64 haswell_get_tohm(struct sbridge_pvt *pvt)
{
	u64 rc;
	u32 reg;

	pci_read_config_dword(pvt->info.pci_vtd, HASWELL_TOHM_0, &reg);
	rc = GET_BITFIELD(reg, 26, 31);
	pci_read_config_dword(pvt->info.pci_vtd, HASWELL_TOHM_1, &reg);
	rc = ((reg << 6) | rc) << 26;

	return rc | 0x1ffffff;
}

static u64 haswell_rir_limit(u32 reg)
{
	return (((u64)GET_BITFIELD(reg,  1, 11) + 1) << 29) - 1;
}

static inline u8 sad_pkg_socket(u8 pkg)
{
	/* on Ivy Bridge, nodeID is SASS, where A is HA and S is node id */
	return ((pkg >> 3) << 2) | (pkg & 0x3);
}

static inline u8 sad_pkg_ha(u8 pkg)
{
	return (pkg >> 2) & 0x1;
}

/****************************************************************************
			Memory check routines
 ****************************************************************************/

static struct pci_dev *get_pdev_same_bus(u8 bus, u32 id)
{
	struct pci_dev *pdev = NULL;

	do {
		pdev = pci_get_device(PCI_VENDOR_ID_INTEL, id, pdev);
		if (pdev && pdev->bus->number == bus)
			break;
	} while (pdev);

	return pdev;
}

/**
 * sbridge_get_active_channels() - gets the number of channels and csrows
 * @bus:	Device bus
 * @type:	Either it's a Sandy Bridge or Ivy Bridge
 * @channels:	Number of channels that will be returned
 * @csrows:	Number of csrows found
 *
 * Since EDAC core needs to know in advance the number of available channels
 * and csrows, in order to allocate memory for csrows/channels, it is needed
 * to run two similar steps. At the first step, implemented on this function,
 * it checks the number of csrows/channels present at one socket, identified
 * by the associated PCI bus.
 * this is used in order to properly allocate the size of mci components.
 * Note: one csrow is one dimm.
 */
static int sbridge_get_active_channels(const u8 bus, enum type type,
				       unsigned *channels, unsigned *csrows)
{
	struct pci_dev *pdev = NULL;
	int i, j;
	u32 mcmtr, id;
	bool ha2 = false;

	*channels = 0;
	*csrows = 0;

	if (type == IVY_BRIDGE)
		id = PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TA;
	else if (type == HASWELL)
		id = PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TA;
	else
		id = PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TA;

	pdev = get_pdev_same_bus(bus, id);
	if (!pdev) {
		sbridge_printk(KERN_ERR, "Couldn't find PCI device "
					"%04x:%04x! on bus %02d\n",
					PCI_VENDOR_ID_INTEL, id, bus);
		return -ENODEV;
	}

	pci_read_config_dword(pdev, MCMTR, &mcmtr);
	if (!IS_ECC_ENABLED(mcmtr)) {
		sbridge_printk(KERN_ERR, "ECC is disabled. Aborting\n");
		return -ENODEV;
	}

	if (type == IVY_BRIDGE && get_pdev_same_bus(bus, PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1))
		ha2 = true;

	for (i = 0; i < NUM_CHANNELS; i++) {
		u32 mtr;

		if (type == SANDY_BRIDGE) {
			/* Device 15 functions 2 - 5  */
			id = PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD0 + i;
		} else if (type == IVY_BRIDGE) {
			/* In 2HA mode, channels 2, 3 are in a different
			 * device */
			if (i < 2 || !ha2)
				id = PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD0 + i;
			else
				id = PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD0 + (i - 2);
		} else if (type == HASWELL) {
			/* In 2HA mode, channels 2, 3 are in a different
			 * device */
			if (i < 2 || !ha2)
				id = PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD0 + i;
			else
				id = PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD0 + (i - 2);
		}
		pdev = get_pdev_same_bus(bus, id);
		if (!pdev) {
			sbridge_printk(KERN_ERR, "Couldn't find PCI device "
						 "%04x:%04x! on bus %02d\n",
						 PCI_VENDOR_ID_INTEL, id, bus);
			return -ENODEV;
		}
		(*channels)++;

		for (j = 0; j < ARRAY_SIZE(mtr_regs); j++) {
			pci_read_config_dword(pdev, mtr_regs[j], &mtr);
			debugf1("Bus#%02x channel #%d  MTR%d = %x\n", bus, i, j, mtr);
			if (IS_DIMM_PRESENT(mtr))
				(*csrows)++;
		}
	}

	debugf0("Number of active channels: %d, number of active dimms: %d\n",
		*channels, *csrows);

	return 0;
}

static int get_dimm_config(const struct mem_ctl_info *mci)
{
	struct sbridge_pvt *pvt = mci->pvt_info;
	struct csrow_info *csr;
	unsigned i, j, banks, ranks, rows, cols, npages;
	u64 size;
	int csrow = 0;
	unsigned long last_page = 0;
	u32 reg;
	enum edac_type mode;
	enum mem_type mtype;

	if (pvt->info.type == HASWELL)
		pci_read_config_dword(pvt->pci_sad1, SAD_TARGET, &reg);
	else
		pci_read_config_dword(pvt->pci_br0, SAD_TARGET, &reg);

	pvt->sbridge_dev->source_id = SOURCE_ID(reg);

	pvt->sbridge_dev->node_id = pvt->info.get_node_id(pvt);
	debugf0("mc#%d: Node ID: %d, source ID: %d\n",
		pvt->sbridge_dev->mc,
		pvt->sbridge_dev->node_id,
		pvt->sbridge_dev->source_id);

	pci_read_config_dword(pvt->pci_ras, RASENABLES, &reg);
	if (IS_MIRROR_ENABLED(reg)) {
		debugf0("Memory mirror is enabled\n");
		pvt->is_mirrored = true;
	} else {
		debugf0("Memory mirror is disabled\n");
		pvt->is_mirrored = false;
	}

	pci_read_config_dword(pvt->pci_ta, MCMTR, &pvt->info.mcmtr);
	if (IS_LOCKSTEP_ENABLED(pvt->info.mcmtr)) {
		debugf0("Lockstep is enabled\n");
		mode = EDAC_S8ECD8ED;
		pvt->is_lockstep = true;
	} else {
		debugf0("Lockstep is disabled\n");
		mode = EDAC_S4ECD4ED;
		pvt->is_lockstep = false;
	}
	if (IS_CLOSE_PG(pvt->info.mcmtr)) {
		debugf0("address map is on closed page mode\n");
		pvt->is_close_pg = true;
	} else {
		debugf0("address map is on open page mode\n");
		pvt->is_close_pg = false;
	}

	mtype = pvt->info.get_memory_type(pvt);
	if (mtype == MEM_RDDR3 || mtype == MEM_RDDR4)
		debugf0("Memory is registered\n");
	else if (mtype == MEM_UNKNOWN)
		debugf0("Cannot determine memory type\n");
	else
		debugf0("Memory is unregistered\n");

	if (mtype == MEM_DDR4 || MEM_RDDR4)
		banks = 16;
	else
		banks = 8;

	for (i = 0; i < NUM_CHANNELS; i++) {
		u32 mtr;

		for (j = 0; j < ARRAY_SIZE(mtr_regs); j++) {
			pci_read_config_dword(pvt->pci_tad[i],
					      mtr_regs[j], &mtr);
			debugf4("Channel #%d  MTR%d = %x\n", i, j, mtr);
			if (IS_DIMM_PRESENT(mtr)) {
				pvt->channel[i].dimms++;

				ranks = numrank(pvt->info.type, mtr);
				rows = numrow(mtr);
				cols = numcol(mtr);

				size = ((u64)rows * cols * banks * ranks) >> (20 - 3);
				npages = MiB_TO_PAGES(size);

				debugf0("mc#%d: channel %d, dimm %d, %Ld Mb (%d pages) bank: %d, rank: %d, row: %#x, col: %#x\n",
					pvt->sbridge_dev->mc, i, j,
					size, npages,
					banks, ranks, rows, cols);
				csr = &mci->csrows[csrow];

				csr->first_page = last_page;
				csr->last_page = last_page + npages - 1;
				csr->page_mask = 0UL;	/* Unused */
				csr->nr_pages = npages;
				csr->grain = 32;
				csr->csrow_idx = csrow;
				switch(banks) {
				case 16:
					csr->dtype = DEV_X16;
					break;
				case 8:
					csr->dtype = DEV_X8;
					break;
				case 4:
					csr->dtype = DEV_X4;
					break;
				}
				csr->ce_count = 0;
				csr->ue_count = 0;
				csr->mtype = mtype;
				csr->edac_mode = mode;
				csr->nr_channels = 1;
				csr->channels[0].chan_idx = i;
				csr->channels[0].ce_count = 0;
				pvt->csrow_map[i][j] = csrow;
				snprintf(csr->channels[0].label,
					 sizeof(csr->channels[0].label),
					 "CPU_SrcID#%u_Channel#%u_DIMM#%u",
					 pvt->sbridge_dev->source_id, i, j);
				last_page += npages;
				csrow++;
			}
		}
	}

	return 0;
}

static void get_memory_layout(const struct mem_ctl_info *mci)
{
	struct sbridge_pvt *pvt = mci->pvt_info;
	int i, j, k, n_sads, n_tads, sad_interl;
	u32 reg;
	u64 limit, prv = 0;
	u64 tmp_mb;
	u32 rir_way;

	/*
	 * Step 1) Get TOLM/TOHM ranges
	 */

	pvt->tolm = pvt->info.get_tolm(pvt);
	tmp_mb = (1 + pvt->tolm) >> 20;

	debugf0("TOLM: %Lu.%03Lu GB (0x%016Lx)\n",
		tmp_mb / 1000, tmp_mb % 1000, (u64)pvt->tolm);

	/* Address range is already 45:25 */
	pvt->tohm = pvt->info.get_tohm(pvt);
	tmp_mb = (1 + pvt->tohm) >> 20;

	debugf0("TOHM: %Lu.%03Lu GB (0x%016Lx)",
		tmp_mb / 1000, tmp_mb % 1000, (u64)pvt->tohm);

	/*
	 * Step 2) Get SAD range and SAD Interleave list
	 * TAD registers contain the interleave wayness. However, it
	 * seems simpler to just discover it indirectly, with the
	 * algorithm bellow.
	 */
	prv = 0;
	for (n_sads = 0; n_sads < pvt->info.max_sad; n_sads++) {
		/* SAD_LIMIT Address range is 45:26 */
		pci_read_config_dword(pvt->pci_sad0, pvt->info.dram_rule[n_sads],
				      &reg);
		limit = SAD_LIMIT(reg);

		if (!DRAM_RULE_ENABLE(reg))
			continue;

		if (limit <= prv)
			break;

		tmp_mb = (limit + 1) >> 20;
		debugf0("SAD#%d %s up to %Lu.%03Lu GB (0x%016Lx) %s reg=0x%08x\n",
			n_sads,
			get_dram_attr(reg),
			tmp_mb / 1000, tmp_mb % 1000,
			((u64)tmp_mb) << 20L,
			INTERLEAVE_MODE(reg) ? "Interleave: 8:6" : "Interleave: [8:6]XOR[18:16]",
			reg);
		prv = limit;

		pci_read_config_dword(pvt->pci_sad0, pvt->info.interleave_list[n_sads],
				      &reg);
		sad_interl = sad_pkg(pvt->info.interleave_pkg, reg, 0);
		for (j = 0; j < 8; j++) {
			u32 pkg = sad_pkg(pvt->info.interleave_pkg, reg, j);
			if (j > 0 && sad_interl == pkg)
				break;

			debugf0("SAD#%d, interleave #%d: %d\n",
			n_sads, j, pkg);
		}
	}

	/*
	 * Step 3) Get TAD range
	 */
	prv = 0;
	for (n_tads = 0; n_tads < MAX_TAD; n_tads++) {
		pci_read_config_dword(pvt->pci_ha0, tad_dram_rule[n_tads],
				      &reg);
		limit = TAD_LIMIT(reg);
		if (limit <= prv)
			break;
		tmp_mb = (limit + 1) >> 20;

		debugf0("TAD#%d: up to %Lu.%03Lu GB (0x%016Lx), socket interleave %d, memory interleave %d, TGT: %d, %d, %d, %d, reg=0x%08x\n",
			n_tads, tmp_mb / 1000, tmp_mb % 1000,
			((u64)tmp_mb) << 20L,
			(u32)TAD_SOCK(reg),
			(u32)TAD_CH(reg),
			(u32)TAD_TGT0(reg),
			(u32)TAD_TGT1(reg),
			(u32)TAD_TGT2(reg),
			(u32)TAD_TGT3(reg),
			reg);
		prv = tmp_mb;
	}

	/*
	 * Step 4) Get TAD offsets, per each channel
	 */
	for (i = 0; i < NUM_CHANNELS; i++) {
		if (!pvt->channel[i].dimms)
			continue;
		for (j = 0; j < n_tads; j++) {
			pci_read_config_dword(pvt->pci_tad[i],
					      tad_ch_nilv_offset[j],
					      &reg);
			tmp_mb = TAD_OFFSET(reg) >> 20;
			debugf0("TAD CH#%d, offset #%d: %Lu.%03Lu GB (0x%016Lx), reg=0x%08x\n",
				i, j,
				tmp_mb / 1000, tmp_mb % 1000,
				((u64)tmp_mb) << 20L,
				reg);
		}
	}

	/*
	 * Step 6) Get RIR Wayness/Limit, per each channel
	 */
	for (i = 0; i < NUM_CHANNELS; i++) {
		if (!pvt->channel[i].dimms)
			continue;
		for (j = 0; j < MAX_RIR_RANGES; j++) {
			pci_read_config_dword(pvt->pci_tad[i],
					      rir_way_limit[j],
					      &reg);

			if (!IS_RIR_VALID(reg))
				continue;

			tmp_mb = pvt->info.rir_limit(reg) >> 20;
			rir_way = 1 << RIR_WAY(reg);
			debugf0("CH#%d RIR#%d, limit: %Lu.%03Lu GB (0x%016Lx), way: %d, reg=0x%08x\n",
				i, j,
				tmp_mb / 1000, tmp_mb % 1000,
				((u64)tmp_mb) << 20L,
				rir_way,
				reg);

			for (k = 0; k < rir_way; k++) {
				pci_read_config_dword(pvt->pci_tad[i],
						      rir_offset[j][k],
						      &reg);
				tmp_mb = RIR_OFFSET(reg) << 6;

				debugf0("CH#%d RIR#%d INTL#%d, offset %Lu.%03Lu GB (0x%016Lx), tgt: %d, reg=0x%08x\n",
					i, j, k,
					tmp_mb / 1000, tmp_mb % 1000,
					((u64)tmp_mb) << 20L,
					(u32)RIR_RNK_TGT(reg),
					reg);
			}
		}
	}
}

struct mem_ctl_info *get_mci_for_node_id(u8 node_id)
{
	struct sbridge_dev *sbridge_dev;

	list_for_each_entry(sbridge_dev, &sbridge_edac_list, list) {
		if (sbridge_dev->node_id == node_id)
			return sbridge_dev->mci;
	}
	return NULL;
}

static int get_memory_error_data(struct mem_ctl_info *mci,
				 u64 addr,
				 u8 *socket,
				 long *channel_mask,
				 u8 *rank,
				 char *area_type)
{
	struct mem_ctl_info	*new_mci;
	struct sbridge_pvt *pvt = mci->pvt_info;
	struct pci_dev		*pci_ha;
	char			msg[256];
	int 			n_rir, n_sads, n_tads, sad_way, sck_xch;
	int			sad_interl, idx, base_ch;
	int			interleave_mode, a7mode, shiftup = 0;
	unsigned		sad_interleave[pvt->info.max_interleave];
	u32			reg;
	u8			ch_way, sck_way, pkg, sad_ha = 0;
	u32			tad_offset;
	u32			rir_way;
	u64			ch_addr, offset, limit = 0, prv = 0;


	/*
	 * Step 0) Check if the address is at special memory ranges
	 * The check bellow is probably enough to fill all cases where
	 * the error is not inside a memory, except for the legacy
	 * range (e. g. VGA addresses). It is unlikely, however, that the
	 * memory controller would generate an error on that range.
	 */
	if ((addr > (u64) pvt->tolm) && (addr < (1L << 32))) {
		sprintf(msg, "Error at TOLM area, on addr 0x%08Lx", addr);
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}
	if (addr >= (u64)pvt->tohm) {
		sprintf(msg, "Error at MMIOH area, on addr 0x%016Lx", addr);
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}

	/*
	 * Step 1) Get socket
	 */
	for (n_sads = 0; n_sads < pvt->info.max_sad; n_sads++) {
		pci_read_config_dword(pvt->pci_sad0, pvt->info.dram_rule[n_sads],
				      &reg);

		if (!DRAM_RULE_ENABLE(reg))
			continue;

		limit = SAD_LIMIT(reg);
		if (limit <= prv) {
			sprintf(msg, "Can't discover the memory socket");
			edac_mc_handle_ce_no_info(mci, msg);
			return -EINVAL;
		}
		if  (addr <= limit)
			break;
		prv = limit;
	}
	if (n_sads == pvt->info.max_sad) {
		sprintf(msg, "Can't discover the memory socket");
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}
	area_type = get_dram_attr(reg);
	interleave_mode = INTERLEAVE_MODE(reg);
	a7mode = A7MODE(reg);

	pci_read_config_dword(pvt->pci_sad0, pvt->info.interleave_list[n_sads],
			      &reg);

	if (pvt->info.type == SANDY_BRIDGE) {
		sad_interl = sad_pkg(pvt->info.interleave_pkg, reg, 0);
		for (sad_way = 0; sad_way < 8; sad_way++) {
			u32 pkg = sad_pkg(pvt->info.interleave_pkg, reg, sad_way);
			if (sad_way > 0 && sad_interl == pkg)
				break;
			sad_interleave[sad_way] = pkg;
			debugf0("SAD interleave #%d: %d\n",
				 sad_way, sad_interleave[sad_way]);
		}
		debugf0("mc#%d: Error detected on SAD#%d: address 0x%016Lx < 0x%016Lx, Interleave [%d:6]%s\n",
			 pvt->sbridge_dev->mc,
			 n_sads,
			 addr,
			 limit,
			 sad_way + 7,
			 !interleave_mode ? "" : "XOR[18:16]");
		if (interleave_mode)
			idx = ((addr >> 6) ^ (addr >> 16)) & 7;
		else
			idx = (addr >> 6) & 7;
		switch (sad_way) {
		case 1:
			idx = 0;
			break;
		case 2:
			idx = idx & 1;
			break;
		case 4:
			idx = idx & 3;
			break;
		case 8:
			break;
		default:
			sprintf(msg, "Can't discover socket interleave");
			return -EINVAL;
		}
		*socket = sad_interleave[idx];
		debugf0("SAD interleave index: %d (wayness %d) = CPU socket %d\n",
			 idx, sad_way, *socket);
	} else if (pvt->info.type == HASWELL) {
		int bits;

		if (a7mode) {
			/* A7 mode swaps P9 with P6 */
			bits = GET_BITFIELD(addr, 7, 8) << 1;
			bits |= GET_BITFIELD(addr, 9, 9);
		} else
			bits = GET_BITFIELD(addr, 7, 9);

		if (interleave_mode) {
			/* interleave mode will XOR {8,7,6} with {18,17,16} */
			idx = GET_BITFIELD(addr, 16, 18);
			idx ^= bits;
		} else
			idx = bits;

		pkg = sad_pkg(pvt->info.interleave_pkg, reg, idx);
		*socket = sad_pkg_socket(pkg);
		sad_ha = sad_pkg_ha(pkg);

		if (a7mode) {
			/* MCChanShiftUpEnable */
			pci_read_config_dword(pvt->pci_ha0,
					      HASWELL_HASYSDEFEATURE2, &reg);
			shiftup = GET_BITFIELD(reg, 22, 22);
		}

		debugf0("SAD interleave package: %d = CPU socket %d, HA %i, shiftup: %i\n",
			idx, *socket, sad_ha, shiftup);
	} else {
		/* Ivy Bridge's SAD mode doesn't support XOR interleave mode */
		idx = (addr >> 6) & 7;
		pkg = sad_pkg(pvt->info.interleave_pkg, reg, idx);
		*socket = sad_pkg_socket(pkg);
		sad_ha = sad_pkg_ha(pkg);
		debugf0("SAD interleave package: %d = CPU socket %d, HA %d\n",
			 idx, *socket, sad_ha);
	}

	/*
	 * Move to the proper node structure, in order to access the
	 * right PCI registers
	 */
	new_mci = get_mci_for_node_id(*socket);
	if (!new_mci) {
		sprintf(msg, "Struct for socket #%u wasn't initialized",
			*socket);
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}
	mci = new_mci;
	pvt = mci->pvt_info;

	/*
	 * Step 2) Get memory channel
	 */
	prv = 0;
	if (pvt->info.type == SANDY_BRIDGE)
		pci_ha = pvt->pci_ha0;
	else {
		if (sad_ha)
			pci_ha = pvt->pci_ha1;
		else
			pci_ha = pvt->pci_ha0;
	}
	for (n_tads = 0; n_tads < MAX_TAD; n_tads++) {
		pci_read_config_dword(pci_ha, tad_dram_rule[n_tads], &reg);
		limit = TAD_LIMIT(reg);
		if (limit <= prv) {
			sprintf(msg, "Can't discover the memory channel");
			edac_mc_handle_ce_no_info(mci, msg);
			return -EINVAL;
		}
		if  (addr <= limit)
			break;
		prv = limit;
	}
	if (n_tads == MAX_TAD) {
		sprintf(msg, "Can't discover the memory channel");
		return -EINVAL;
	}

	ch_way = TAD_CH(reg) + 1;
	sck_way = TAD_SOCK(reg) + 1;

	if (ch_way == 3)
		idx = addr >> 6;
	else
		idx = (addr >> (6 + sck_way + shiftup)) & 0x3;
	idx = idx % ch_way;

	/*
	 * FIXME: Shouldn't we use CHN_IDX_OFFSET() here, when ch_way == 3 ???
	 */
	switch (idx) {
	case 0:
		base_ch = TAD_TGT0(reg);
		break;
	case 1:
		base_ch = TAD_TGT1(reg);
		break;
	case 2:
		base_ch = TAD_TGT2(reg);
		break;
	case 3:
		base_ch = TAD_TGT3(reg);
		break;
	default:
		sprintf(msg, "Can't discover the TAD target");
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}
	*channel_mask = 1 << base_ch;

	pci_read_config_dword(pvt->pci_tad[base_ch],
				tad_ch_nilv_offset[n_tads],
				&tad_offset);

	if (pvt->is_mirrored) {
		*channel_mask |= 1 << ((base_ch + 2) % 4);
		switch(ch_way) {
		case 2:
		case 4:
			sck_xch = 1 << sck_way * (ch_way >> 1);
			break;
		default:
			sprintf(msg, "Invalid mirror set. Can't decode addr");
			edac_mc_handle_ce_no_info(mci, msg);
			return -EINVAL;
		}
	} else
		sck_xch = (1 << sck_way) * ch_way;

	if (pvt->is_lockstep)
		*channel_mask |= 1 << ((base_ch + 1) % 4);

	offset = TAD_OFFSET(tad_offset);

	debugf0("TAD#%d: address 0x%016Lx < 0x%016Lx, socket interleave %d, channel interleave %d (offset 0x%08Lx), index %d, base ch: %d, ch mask: 0x%02lx\n",
		n_tads,
		addr,
		limit,
		(u32)TAD_SOCK(reg),
		ch_way,
		offset,
		idx,
		base_ch,
		*channel_mask);

	/* Calculate channel address */
	/* Remove the TAD offset */

	if (offset > addr) {
		sprintf(msg, "Can't calculate ch addr: TAD offset 0x%08Lx is too high for addr 0x%08Lx!",
			offset, addr);
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}
	addr -= offset;
	/* Store the low bits [0:6] of the addr */
	ch_addr = addr & 0x7f;
	/* Remove socket wayness and remove 6 bits */
	addr >>= 6;
	addr = div_u64(addr, sck_xch);
#if 0
	/* Divide by channel way */
	addr = addr / ch_way;
#endif
	/* Recover the last 6 bits */
	ch_addr |= addr << 6;

	/*
	 * Step 3) Decode rank
	 */
	for (n_rir = 0; n_rir < MAX_RIR_RANGES; n_rir++) {
		pci_read_config_dword(pvt->pci_tad[base_ch],
				      rir_way_limit[n_rir],
				      &reg);

		if (!IS_RIR_VALID(reg))
			continue;

		limit = pvt->info.rir_limit(reg);

		debugf0("RIR#%d, limit: %Lu.%03Lu GB (0x%016Lx), way: %d\n",
			n_rir,
			(limit >> 20) / 1000, (limit >> 20) % 1000,
			limit,
			1 << RIR_WAY(reg));
		if  (ch_addr <= limit)
			break;
	}
	if (n_rir == MAX_RIR_RANGES) {
		sprintf(msg, "Can't discover the memory rank for ch addr 0x%08Lx",
			ch_addr);
		edac_mc_handle_ce_no_info(mci, msg);
		return -EINVAL;
	}
	rir_way = RIR_WAY(reg);

	if (pvt->is_close_pg)
		idx = (ch_addr >> 6);
	else
		idx = (ch_addr >> 13);	/* FIXME: Datasheet says to shift by 15 */
	idx %= 1 << rir_way;

	pci_read_config_dword(pvt->pci_tad[base_ch],
			      rir_offset[n_rir][idx],
			      &reg);
	*rank = RIR_RNK_TGT(reg);

	debugf0("RIR#%d: channel address 0x%08Lx < 0x%08Lx, RIR interleave %d, index %d\n",
		n_rir,
		ch_addr,
		limit,
		rir_way,
		idx);

	return 0;
}

/****************************************************************************
	Device initialization routines: put/get, init/exit
 ****************************************************************************/

/*
 *	sbridge_put_all_devices	'put' all the devices that we have
 *				reserved via 'get'
 */
static void sbridge_put_devices(struct sbridge_dev *sbridge_dev)
{
	int i;

	debugf0(__FILE__ ": %s()\n", __func__);
	for (i = 0; i < sbridge_dev->n_devs; i++) {
		struct pci_dev *pdev = sbridge_dev->pdev[i];
		if (!pdev)
			continue;
		debugf0("Removing dev %02x:%02x.%d\n",
			pdev->bus->number,
			PCI_SLOT(pdev->devfn), PCI_FUNC(pdev->devfn));
		pci_dev_put(pdev);
	}
}

static void sbridge_put_all_devices(void)
{
	struct sbridge_dev *sbridge_dev, *tmp;

	list_for_each_entry_safe(sbridge_dev, tmp, &sbridge_edac_list, list) {
		sbridge_put_devices(sbridge_dev);
		free_sbridge_dev(sbridge_dev);
	}
}

static int sbridge_get_onedevice(struct pci_dev **prev,
				 u8 *num_mc,
				 const struct pci_id_table *table,
				 const unsigned devno)
{
	struct sbridge_dev *sbridge_dev;
	const struct pci_id_descr *dev_descr = &table->descr[devno];
	struct pci_dev *pdev = NULL;
	u8 bus = 0;

	sbridge_printk(KERN_INFO,
		"Seeking for: PCI ID %04x:%04x\n",
		PCI_VENDOR_ID_INTEL, dev_descr->dev_id);

	pdev = pci_get_device(PCI_VENDOR_ID_INTEL,
			      dev_descr->dev_id, *prev);

	if (!pdev) {
		if (*prev) {
			*prev = pdev;
			return 0;
		}

		if (dev_descr->optional)
			return 0;

		/* if the HA wasn't found */
		if (devno == 0)
			return -ENODEV;

		sbridge_printk(KERN_INFO,
			"Device not found: %04x:%04x\n",
			PCI_VENDOR_ID_INTEL, dev_descr->dev_id);

		/* End of list, leave */
		return -ENODEV;
	}
	bus = pdev->bus->number;

	sbridge_dev = get_sbridge_dev(bus);
	if (!sbridge_dev) {
		sbridge_dev = alloc_sbridge_dev(bus, table);
		if (!sbridge_dev) {
			pci_dev_put(pdev);
			return -ENOMEM;
		}
		(*num_mc)++;
	}

	if (sbridge_dev->pdev[devno]) {
		sbridge_printk(KERN_ERR,
			"Duplicated device for %04x:%04x\n",
			PCI_VENDOR_ID_INTEL, dev_descr->dev_id);
		pci_dev_put(pdev);
		return -ENODEV;
	}

	sbridge_dev->pdev[devno] = pdev;

	/* Be sure that the device is enabled */
	if (unlikely(pci_enable_device(pdev) < 0)) {
		sbridge_printk(KERN_ERR,
			"Couldn't enable %04x:%04x\n",
			PCI_VENDOR_ID_INTEL, dev_descr->dev_id);
		return -ENODEV;
	}

	debugf0("Detected %04x:%04x\n",
		PCI_VENDOR_ID_INTEL, dev_descr->dev_id);

	/*
	 * As stated on drivers/pci/search.c, the reference count for
	 * @from is always decremented if it is not %NULL. So, as we need
	 * to get all devices up to null, we need to do a get for the device
	 */
	pci_dev_get(pdev);

	*prev = pdev;

	return 0;
}

/*
 * sbridge_get_all_devices - Find and perform 'get' operation on the MCH's
 *			     devices we want to reference for this driver.
 * @num_mc: pointer to the memory controllers count, to be incremented in case
 * 	    of success.
 * @table: model specific table
 *
 * returns 0 in case of success or error code
 */
static int sbridge_get_all_devices(u8 *num_mc,
				   const struct pci_id_table *table)
{
	int i, rc;
	struct pci_dev *pdev = NULL;

	while (table && table->descr) {
		for (i = 0; i < table->n_devs; i++) {
			pdev = NULL;
			do {
				rc = sbridge_get_onedevice(&pdev, num_mc,
							   table, i);
				if (rc < 0) {
					if (i == 0) {
						i = table->n_devs;
						break;
					}
					sbridge_put_all_devices();
					return -ENODEV;
				}
			} while (pdev);
		}
		table++;
	}

	return 0;
}

static int sbridge_mci_bind_devs(struct mem_ctl_info *mci,
				 struct sbridge_dev *sbridge_dev)
{
	struct sbridge_pvt *pvt = mci->pvt_info;
	struct pci_dev *pdev;
	int i;

	for (i = 0; i < sbridge_dev->n_devs; i++) {
		pdev = sbridge_dev->pdev[i];
		if (!pdev)
			continue;

		switch (pdev->device) {
		case PCI_DEVICE_ID_INTEL_SBRIDGE_SAD0:
			pvt->pci_sad0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_SAD1:
			pvt->pci_sad1 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_BR:
			pvt->pci_br0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_HA0:
			pvt->pci_ha0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TA:
			pvt->pci_ta = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_RAS:
			pvt->pci_ras = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD0:
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD1:
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD2:
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD3:
		{
			int id = pdev->device - PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TAD0;
			pvt->pci_tad[id] = pdev;
		}
			break;
		case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_DDRIO:
			pvt->pci_ddrio = pdev;
			break;
		default:
			goto error;
		}

		debugf0("Associated PCI %02x:%02x, bus %d with dev = %p\n",
			pdev->vendor, pdev->device,
			sbridge_dev->bus,
			pdev);
	}

	/* Check if everything were registered */
	if (!pvt->pci_sad0 || !pvt->pci_sad1 || !pvt->pci_ha0 ||
	    !pvt-> pci_tad || !pvt->pci_ras  || !pvt->pci_ta)
		goto enodev;

	for (i = 0; i < NUM_CHANNELS; i++) {
		if (!pvt->pci_tad[i])
			goto enodev;
	}
	return 0;

enodev:
	sbridge_printk(KERN_ERR, "Some needed devices are missing\n");
	return -ENODEV;

error:
	sbridge_printk(KERN_ERR, "Unexpected device %02x:%02x\n",
		       PCI_VENDOR_ID_INTEL, pdev->device);
	return -EINVAL;
}

static int ibridge_mci_bind_devs(struct mem_ctl_info *mci,
				 struct sbridge_dev *sbridge_dev)
{
	struct sbridge_pvt *pvt = mci->pvt_info;
	struct pci_dev *pdev, *tmp;
	int i;
	bool mode_2ha = false;

	tmp = pci_get_device(PCI_VENDOR_ID_INTEL,
			     PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1, NULL);
	if (tmp) {
		mode_2ha = true;
		pci_dev_put(tmp);
	}

	for (i = 0; i < sbridge_dev->n_devs; i++) {
		pdev = sbridge_dev->pdev[i];
		if (!pdev)
			continue;

		switch (pdev->device) {
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0:
			pvt->pci_ha0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TA:
			pvt->pci_ta = pdev;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_RAS:
			pvt->pci_ras = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD2:
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD3:
			/* if we have 2 HAs active, channels 2 and 3
			 * are in other device */
			if (mode_2ha)
				break;
			/* fall through */
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD0:
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD1:
		{
			int id = pdev->device - PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TAD0;
			pvt->pci_tad[id] = pdev;
		}
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_2HA_DDRIO0:
			pvt->pci_ddrio = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_1HA_DDRIO0:
			if (!mode_2ha)
				pvt->pci_ddrio = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_SAD:
			pvt->pci_sad0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_BR0:
			pvt->pci_br0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_BR1:
			pvt->pci_br1 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1:
			pvt->pci_ha1 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD0:
		case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD1:
		{
			int id = pdev->device - PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA1_TAD0 + 2;

			/* we shouldn't have this device if we have just one
			 * HA present */
			WARN_ON(!mode_2ha);
			pvt->pci_tad[id] = pdev;
		}
			break;
		default:
			goto error;
		}

		debugf0("Associated PCI %02x.%02d.%d with dev = %p\n",
			sbridge_dev->bus,
			PCI_SLOT(pdev->devfn), PCI_FUNC(pdev->devfn),
			pdev);
	}

	/* Check if everything were registered */
	if (!pvt->pci_sad0 || !pvt->pci_ha0 || !pvt->pci_br0 ||
	    !pvt->pci_br1 || !pvt->pci_tad || !pvt->pci_ras  ||
	    !pvt->pci_ta)
		goto enodev;

	for (i = 0; i < NUM_CHANNELS; i++) {
		if (!pvt->pci_tad[i])
			goto enodev;
	}
	return 0;

enodev:
	sbridge_printk(KERN_ERR, "Some needed devices are missing\n");
	return -ENODEV;

error:
	sbridge_printk(KERN_ERR,
		       "Unexpected device %02x:%02x\n", PCI_VENDOR_ID_INTEL,
			pdev->device);
	return -EINVAL;
}

static int haswell_mci_bind_devs(struct mem_ctl_info *mci,
				 struct sbridge_dev *sbridge_dev)
{
	struct sbridge_pvt *pvt = mci->pvt_info;
	struct pci_dev *pdev, *tmp;
	int i;
	bool mode_2ha = false;

	tmp = pci_get_device(PCI_VENDOR_ID_INTEL,
			     PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1, NULL);
	if (tmp) {
		mode_2ha = true;
		pci_dev_put(tmp);
	}

	/* there's only one device per system; not tied to any bus */
	if (pvt->info.pci_vtd == NULL)
		/* result will be checked later */
		pvt->info.pci_vtd = pci_get_device(PCI_VENDOR_ID_INTEL,
						   PCI_DEVICE_ID_INTEL_HASWELL_IMC_VTD_MISC,
						   NULL);

	for (i = 0; i < sbridge_dev->n_devs; i++) {
		pdev = sbridge_dev->pdev[i];
		if (!pdev)
			continue;

		switch (pdev->device) {
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_CBO_SAD0:
			pvt->pci_sad0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_CBO_SAD1:
			pvt->pci_sad1 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0:
			pvt->pci_ha0 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TA:
			pvt->pci_ta = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_THERMAL:
			pvt->pci_ras = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD0:
			pvt->pci_tad[0] = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD1:
			pvt->pci_tad[1] = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD2:
			if (!mode_2ha)
				pvt->pci_tad[2] = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0_TAD3:
			if (!mode_2ha)
				pvt->pci_tad[3] = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_DDRIO0:
			pvt->pci_ddrio = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1:
			pvt->pci_ha1 = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TA:
			pvt->pci_ha1_ta = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD0:
			if (mode_2ha)
				pvt->pci_tad[2] = pdev;
			break;
		case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA1_TAD1:
			if (mode_2ha)
				pvt->pci_tad[3] = pdev;
			break;
		default:
			break;
		}

		debugf0("Associated PCI %02x.%02d.%d with dev = %p\n",
			sbridge_dev->bus,
			PCI_SLOT(pdev->devfn), PCI_FUNC(pdev->devfn),
			pdev);
	}

	/* Check if everything were registered */
	if (!pvt->pci_sad0 || !pvt->pci_ha0 || !pvt->pci_sad1 ||
	    !pvt->pci_ras  || !pvt->pci_ta || !pvt->info.pci_vtd)
		goto enodev;

	for (i = 0; i < NUM_CHANNELS; i++) {
		if (!pvt->pci_tad[i])
			goto enodev;
	}
	return 0;

enodev:
	sbridge_printk(KERN_ERR, "Some needed devices are missing\n");
	return -ENODEV;
}

/****************************************************************************
			Error check routines
 ****************************************************************************/

/*
 * While Sandy Bridge has error count registers, SMI BIOS read values from
 * and resets the counters. So, they are not reliable for the OS to read
 * from them. So, we have no option but to just trust on whatever MCE is
 * telling us about the errors.
 */
static void sbridge_mce_output_error(struct mem_ctl_info *mci,
				    const struct mce *m)
{
	struct mem_ctl_info *new_mci;
	struct sbridge_pvt *pvt = mci->pvt_info;
	char *type, *optype, *msg, *recoverable_msg;
	bool ripv = GET_BITFIELD(m->mcgstatus, 0, 0);
	bool overflow = GET_BITFIELD(m->status, 62, 62);
	bool uncorrected_error = GET_BITFIELD(m->status, 61, 61);
	bool recoverable;
	u32 core_err_cnt = GET_BITFIELD(m->status, 38, 52);
	u32 mscod = GET_BITFIELD(m->status, 16, 31);
	u32 errcode = GET_BITFIELD(m->status, 0, 15);
	u32 channel = GET_BITFIELD(m->status, 0, 3);
	u32 optypenum = GET_BITFIELD(m->status, 4, 6);
	long channel_mask, first_channel;
	u8  rank, socket;
	int csrow, rc, dimm;
	char *area_type = "Unknown";

	if (pvt->info.type == IVY_BRIDGE)
		recoverable = true;
	else
		recoverable = GET_BITFIELD(m->status, 56, 56);

	if (ripv)
		type = "NON_FATAL";
	else
		type = "FATAL";

	/*
	 * According with Table 15-9 of the Intel Archictecture spec vol 3A,
	 * memory errors should fit in this mask:
	 *	000f 0000 1mmm cccc (binary)
	 * where:
	 *	f = Correction Report Filtering Bit. If 1, subsequent errors
	 *	    won't be shown
	 *	mmm = error type
	 *	cccc = channel
	 * If the mask doesn't match, report an error to the parsing logic
	 */
	if (! ((errcode & 0xef80) == 0x80)) {
		optype = "Can't parse: it is not a mem";
	} else {
		switch (optypenum) {
		case 0:
			optype = "generic undef request";
			break;
		case 1:
			optype = "memory read";
			break;
		case 2:
			optype = "memory write";
			break;
		case 3:
			optype = "addr/cmd";
			break;
		case 4:
			optype = "memory scrubbing";
			break;
		default:
			optype = "reserved";
			break;
		}
	}

	/* Only decode errors with an valid address (ADDRV) */
	if (!GET_BITFIELD(m->status, 58, 58))
		return;

	rc = get_memory_error_data(mci, m->addr, &socket,
				   &channel_mask, &rank, area_type);
	if (rc < 0)
		return;
	new_mci = get_mci_for_node_id(socket);
	if (!new_mci) {
		edac_mc_handle_ce_no_info(mci, "Error: socket got corrupted!");
		return;
	}
	mci = new_mci;
	pvt = mci->pvt_info;

	first_channel = find_first_bit(&channel_mask, NUM_CHANNELS);

	if (rank < 4)
		dimm = 0;
	else if (rank < 8)
		dimm = 1;
	else
		dimm = 2;

	csrow = pvt->csrow_map[first_channel][dimm];

	if (uncorrected_error && recoverable)
		recoverable_msg = " recoverable";
	else
		recoverable_msg = "";

	/*
	 * FIXME: What should we do with "channel" information on mcelog?
	 * Probably, we can just discard it, as the channel information
	 * comes from the get_memory_error_data() address decoding
	 */
	msg = kasprintf(GFP_ATOMIC,
			"%d %s error(s): %s on %s area %s%s: cpu=%d Err=%04x:%04x (ch=%d), "
			"addr = 0x%08llx => socket=%d, Channel=%ld(mask=%ld), rank=%d\n",
			core_err_cnt,
			area_type,
			optype,
			type,
			recoverable_msg,
			overflow ? "OVERFLOW" : "",
			m->cpu,
			mscod, errcode,
			channel,		/* 1111b means not specified */
			(long long) m->addr,
			socket,
			first_channel,		/* This is the real channel on SB */
			channel_mask,
			rank);

	debugf0("%s", msg);

	/* Call the helper to output message */
	if (uncorrected_error)
		edac_mc_handle_fbd_ue(mci, csrow, 0, 0, msg);
	else
		edac_mc_handle_fbd_ce(mci, csrow, 0, msg);

	kfree(msg);
}

/*
 *	sbridge_check_error	Retrieve and process errors reported by the
 *				hardware. Called by the Core module.
 */
static void sbridge_check_error(struct mem_ctl_info *mci)
{
	struct sbridge_pvt *pvt = mci->pvt_info;
	int i;
	unsigned count = 0;
	struct mce *m;

	/*
	 * MCE first step: Copy all mce errors into a temporary buffer
	 * We use a double buffering here, to reduce the risk of
	 * loosing an error.
	 */
	smp_rmb();
	count = (pvt->mce_out + MCE_LOG_LEN - pvt->mce_in)
		% MCE_LOG_LEN;
	if (!count)
		return;

	m = pvt->mce_outentry;
	if (pvt->mce_in + count > MCE_LOG_LEN) {
		unsigned l = MCE_LOG_LEN - pvt->mce_in;

		memcpy(m, &pvt->mce_entry[pvt->mce_in], sizeof(*m) * l);
		smp_wmb();
		pvt->mce_in = 0;
		count -= l;
		m += l;
	}
	memcpy(m, &pvt->mce_entry[pvt->mce_in], sizeof(*m) * count);
	smp_wmb();
	pvt->mce_in += count;

	smp_rmb();
	if (pvt->mce_overrun) {
		sbridge_printk(KERN_ERR, "Lost %d memory errors\n",
			      pvt->mce_overrun);
		smp_wmb();
		pvt->mce_overrun = 0;
	}

	/*
	 * MCE second step: parse errors and display
	 */
	for (i = 0; i < count; i++)
		sbridge_mce_output_error(mci, &pvt->mce_outentry[i]);
}

/*
 * sbridge_mce_check_error	Replicates mcelog routine to get errors
 *				This routine simply queues mcelog errors, and
 *				return. The error itself should be handled later
 *				by sbridge_check_error.
 * WARNING: As this routine should be called at NMI time, extra care should
 * be taken to avoid deadlocks, and to be as fast as possible.
 */
static int sbridge_mce_check_error(struct notifier_block *nb, unsigned long val,
				   void *data)
{
	struct mce *mce = (struct mce *)data;
	struct mem_ctl_info *mci;
	struct sbridge_pvt *pvt;

	if (get_edac_report_status() == EDAC_REPORTING_DISABLED)
		return NOTIFY_DONE;

	mci = get_mci_for_node_id(mce->socketid);
	if (!mci)
		return NOTIFY_BAD;
	pvt = mci->pvt_info;

	/*
	 * Just let mcelog handle it if the error is
	 * outside the memory controller. A memory error
	 * is indicated by bit 7 = 1 and bits = 8-11,13-15 = 0.
	 * bit 12 has an special meaning.
	 */
	if ((mce->status & 0xefff) >> 7 != 1)
		return NOTIFY_DONE;

	printk("sbridge: HANDLING MCE MEMORY ERROR\n");

	printk("CPU %d: Machine Check Exception: %Lx Bank %d: %016Lx\n",
	       mce->extcpu, mce->mcgstatus, mce->bank, mce->status);
	printk("TSC %llx ", mce->tsc);
	printk("ADDR %llx ", mce->addr);
	printk("MISC %llx ", mce->misc);

	printk("PROCESSOR %u:%x TIME %llu SOCKET %u APIC %x\n",
		mce->cpuvendor, mce->cpuid, mce->time,
		mce->socketid, mce->apicid);

	smp_rmb();
	if ((pvt->mce_out + 1) % MCE_LOG_LEN == pvt->mce_in) {
		smp_wmb();
		pvt->mce_overrun++;
		return NOTIFY_DONE;
	}

	/* Copy memory error at the ringbuffer */
	memcpy(&pvt->mce_entry[pvt->mce_out], mce, sizeof(*mce));
	smp_wmb();
	pvt->mce_out = (pvt->mce_out + 1) % MCE_LOG_LEN;

	/* Handle fatal errors immediately */
	if (mce->mcgstatus & 1)
		sbridge_check_error(mci);

	/* Advice mcelog that the error were handled */
	return NOTIFY_STOP;
}

static struct notifier_block sbridge_mce_dec = {
	.notifier_call      = sbridge_mce_check_error,
};

/****************************************************************************
			EDAC register/unregister logic
 ****************************************************************************/

static void sbridge_unregister_mci(struct sbridge_dev *sbridge_dev)
{
	struct mem_ctl_info *mci = sbridge_dev->mci;
	struct sbridge_pvt *pvt;

	if (unlikely(!mci || !mci->pvt_info)) {
		debugf0("MC: " __FILE__ ": %s(): dev = %p\n",
			__func__, &sbridge_dev->pdev[0]->dev);

		sbridge_printk(KERN_ERR, "Couldn't find mci handler\n");
		return;
	}

	pvt = mci->pvt_info;

	debugf0("MC: " __FILE__ ": %s(): mci = %p, dev = %p\n",
		__func__, mci, &sbridge_dev->pdev[0]->dev);

	/* Remove MC sysfs nodes */
	edac_mc_del_mc(mci->dev);

	debugf1("%s: free mci struct\n", mci->ctl_name);
	kfree(mci->ctl_name);
	edac_mc_free(mci);
	sbridge_dev->mci = NULL;
}

static int sbridge_register_mci(struct sbridge_dev *sbridge_dev, enum type type)
{
	struct mem_ctl_info *mci;
	struct sbridge_pvt *pvt;
	struct pci_dev *pdev = sbridge_dev->pdev[0];
	int rc, channels, csrows;

	/* Check the number of active and not disabled channels */
	rc = sbridge_get_active_channels(sbridge_dev->bus, type, &channels, &csrows);
	if (unlikely(rc < 0))
		return rc;

	/* allocate a new MC control structure */
	mci = edac_mc_alloc(sizeof(*pvt), csrows, channels, sbridge_dev->mc);
	if (unlikely(!mci))
		return -ENOMEM;

	debugf0("MC: " __FILE__ ": %s(): mci = %p, dev = %p\n",
		__func__, mci, &pdev->dev);

	pvt = mci->pvt_info;
	memset(pvt, 0, sizeof(*pvt));

	/* Associate sbridge_dev and mci for future usage */
	pvt->sbridge_dev = sbridge_dev;
	sbridge_dev->mci = mci;

	mci->mtype_cap = MEM_FLAG_DDR3;
	mci->edac_ctl_cap = EDAC_FLAG_NONE;
	mci->edac_cap = EDAC_FLAG_NONE;
	mci->mod_name = "sbridge_edac.c";
	mci->mod_ver = SBRIDGE_REVISION;
	mci->dev_name = pci_name(pdev);
	mci->ctl_page_to_phys = NULL;

	/* Set the function pointer to an actual operation function */
	mci->edac_check = sbridge_check_error;

	pvt->info.type = type;
	switch (type) {
	case IVY_BRIDGE:
		pvt->info.rankcfgr = IB_RANK_CFG_A;
		pvt->info.get_tolm = ibridge_get_tolm;
		pvt->info.get_tohm = ibridge_get_tohm;
		pvt->info.dram_rule = ibridge_dram_rule;
		pvt->info.get_memory_type = get_memory_type;
		pvt->info.get_node_id = get_node_id;
		pvt->info.rir_limit = rir_limit;
		pvt->info.max_sad = ARRAY_SIZE(ibridge_dram_rule);
		pvt->info.interleave_list = ibridge_interleave_list;
		pvt->info.max_interleave = ARRAY_SIZE(ibridge_interleave_list);
		pvt->info.interleave_pkg = ibridge_interleave_pkg;
		mci->ctl_name = kasprintf(GFP_KERNEL, "Ivy Bridge Socket#%d", mci->mc_idx);

		/* Store pci devices at mci for faster access */
		rc = ibridge_mci_bind_devs(mci, sbridge_dev);
		if (unlikely(rc < 0))
			goto fail0;
		break;
	case SANDY_BRIDGE:
		pvt->info.rankcfgr = SB_RANK_CFG_A;
		pvt->info.get_tolm = sbridge_get_tolm;
		pvt->info.get_tohm = sbridge_get_tohm;
		pvt->info.dram_rule = sbridge_dram_rule;
		pvt->info.get_memory_type = get_memory_type;
		pvt->info.get_node_id = get_node_id;
		pvt->info.rir_limit = rir_limit;
		pvt->info.max_sad = ARRAY_SIZE(sbridge_dram_rule);
		pvt->info.interleave_list = sbridge_interleave_list;
		pvt->info.max_interleave = ARRAY_SIZE(sbridge_interleave_list);
		pvt->info.interleave_pkg = sbridge_interleave_pkg;
		mci->ctl_name = kasprintf(GFP_KERNEL, "Sandy Bridge Socket#%d", mci->mc_idx);

		/* Store pci devices at mci for faster access */
		rc = sbridge_mci_bind_devs(mci, sbridge_dev);
		if (unlikely(rc < 0))
			goto fail0;
		break;
	case HASWELL:
		/* rankcfgr isn't used */
		pvt->info.get_tolm = haswell_get_tolm;
		pvt->info.get_tohm = haswell_get_tohm;
		pvt->info.dram_rule = ibridge_dram_rule;
		pvt->info.get_memory_type = haswell_get_memory_type;
		pvt->info.get_node_id = haswell_get_node_id;
		pvt->info.rir_limit = haswell_rir_limit;
		pvt->info.max_sad = ARRAY_SIZE(ibridge_dram_rule);
		pvt->info.interleave_list = ibridge_interleave_list;
		pvt->info.max_interleave = ARRAY_SIZE(ibridge_interleave_list);
		pvt->info.interleave_pkg = ibridge_interleave_pkg;
		mci->ctl_name = kasprintf(GFP_KERNEL, "Haswell Socket#%d", mci->mc_idx);

		/* Store pci devices at mci for faster access */
		rc = haswell_mci_bind_devs(mci, sbridge_dev);
		if (unlikely(rc < 0))
			goto fail0;
		break;
	}

	/* Get dimm basic config and the memory layout */
	get_dimm_config(mci);
	get_memory_layout(mci);

	/* record ptr to the generic device */
	mci->dev = &pdev->dev;

	/* add this new MC control structure to EDAC's list of MCs */
	if (unlikely(edac_mc_add_mc(mci))) {
		debugf0("MC: " __FILE__
			": %s(): failed edac_mc_add_mc()\n", __func__);
		rc = -EINVAL;
		goto fail0;
	}

	return 0;

fail0:
	kfree(mci->ctl_name);
	edac_mc_free(mci);
	sbridge_dev->mci = NULL;
	return rc;
}

/*
 *	sbridge_probe	Probe for ONE instance of device to see if it is
 *			present.
 *	return:
 *		0 for FOUND a device
 *		< 0 for error code
 */

static int __devinit sbridge_probe(struct pci_dev *pdev,
				  const struct pci_device_id *id)
{
	int rc = -ENODEV;
	u8 mc, num_mc = 0;
	struct sbridge_dev *sbridge_dev;
	enum type type = SANDY_BRIDGE;

	/* get the pci devices we want to reserve for our use */
	mutex_lock(&sbridge_edac_lock);

	/*
	 * All memory controllers are allocated at the first pass.
	 */
	if (unlikely(probed >= 1)) {
		mutex_unlock(&sbridge_edac_lock);
		return -ENODEV;
	}
	probed++;

	switch (pdev->device) {
	case PCI_DEVICE_ID_INTEL_IBRIDGE_IMC_HA0_TA:
		rc = sbridge_get_all_devices(&num_mc, pci_dev_descr_ibridge_table);
		type = IVY_BRIDGE;
		break;
	case PCI_DEVICE_ID_INTEL_SBRIDGE_IMC_TA:
		rc = sbridge_get_all_devices(&num_mc, pci_dev_descr_sbridge_table);
		type = SANDY_BRIDGE;
		break;
	case PCI_DEVICE_ID_INTEL_HASWELL_IMC_HA0:
		rc = sbridge_get_all_devices(&num_mc, pci_dev_descr_haswell_table);
		type = HASWELL;
		break;
	}
	if (unlikely(rc < 0))
		goto fail0;
	mc = 0;

	list_for_each_entry(sbridge_dev, &sbridge_edac_list, list) {
		debugf0("Registering MC#%d (%d of %d)\n", mc, mc + 1, num_mc);
		sbridge_dev->mc = mc++;
		rc = sbridge_register_mci(sbridge_dev, type);
		if (unlikely(rc < 0))
			goto fail1;
	}

	sbridge_printk(KERN_INFO, "Driver loaded.\n");

	mutex_unlock(&sbridge_edac_lock);
	return 0;

fail1:
	list_for_each_entry(sbridge_dev, &sbridge_edac_list, list)
		sbridge_unregister_mci(sbridge_dev);

	sbridge_put_all_devices();
fail0:
	mutex_unlock(&sbridge_edac_lock);
	return rc;
}

/*
 *	sbridge_remove	destructor for one instance of device
 *
 */
static void __devexit sbridge_remove(struct pci_dev *pdev)
{
	struct sbridge_dev *sbridge_dev;

	debugf0(__FILE__ ": %s()\n", __func__);

	/*
	 * we have a trouble here: pdev value for removal will be wrong, since
	 * it will point to the X58 register used to detect that the machine
	 * is a Nehalem or upper design. However, due to the way several PCI
	 * devices are grouped together to provide MC functionality, we need
	 * to use a different method for releasing the devices
	 */

	mutex_lock(&sbridge_edac_lock);

	if (unlikely(!probed)) {
		mutex_unlock(&sbridge_edac_lock);
		return;
	}

	list_for_each_entry(sbridge_dev, &sbridge_edac_list, list)
		sbridge_unregister_mci(sbridge_dev);

	/* Release PCI resources */
	sbridge_put_all_devices();

	probed--;

	mutex_unlock(&sbridge_edac_lock);
}

MODULE_DEVICE_TABLE(pci, sbridge_pci_tbl);

/*
 *	sbridge_driver	pci_driver structure for this module
 *
 */
static struct pci_driver sbridge_driver = {
	.name     = "sbridge_edac",
	.probe    = sbridge_probe,
	.remove   = __devexit_p(sbridge_remove),
	.id_table = sbridge_pci_tbl,
};

/*
 *	sbridge_init		Module entry function
 *			Try to initialize this module for its devices
 */
static int __init sbridge_init(void)
{
	int pci_rc;

	debugf2("MC: " __FILE__ ": %s()\n", __func__);

	/* Ensure that the OPSTATE is set correctly for POLL or NMI */
	opstate_init();

	pci_rc = pci_register_driver(&sbridge_driver);
	if (pci_rc >= 0) {
		mce_register_decode_chain(&sbridge_mce_dec);
		if (get_edac_report_status() == EDAC_REPORTING_DISABLED)
			sbridge_printk(KERN_WARNING, "Loading driver, error reporting disabled.\n");
		return 0;
	}

	sbridge_printk(KERN_ERR, "Failed to register device with error %d.\n",
		      pci_rc);

	return pci_rc;
}

/*
 *	sbridge_exit()	Module exit function
 *			Unregister the driver
 */
static void __exit sbridge_exit(void)
{
	debugf2("MC: " __FILE__ ": %s()\n", __func__);
	pci_unregister_driver(&sbridge_driver);
	mce_unregister_decode_chain(&sbridge_mce_dec);
}

module_init(sbridge_init);
module_exit(sbridge_exit);

module_param(edac_op_state, int, 0444);
MODULE_PARM_DESC(edac_op_state, "EDAC Error Reporting state: 0=Poll,1=NMI");

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Mauro Carvalho Chehab <mchehab@redhat.com>");
MODULE_AUTHOR("Red Hat Inc. (http://www.redhat.com)");
MODULE_DESCRIPTION("MC Driver for Intel Sandy Bridge and Ivy Bridge memory controllers - "
		   SBRIDGE_REVISION);
