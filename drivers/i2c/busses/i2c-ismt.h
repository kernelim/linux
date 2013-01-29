#ifndef _I2C_ISMT_H_
#define _I2C_ISMT_H_

/* PCI Address Constants */
#define SMBBAR		0

/* PCI DIDs for Briarwood's pair of SMBus Message Transport (SMT) Devices */
#define PCI_DEVICE_ID_INTEL_BWD_SMBUS_SMT0 0x0c59
#define PCI_DEVICE_ID_INTEL_BWD_SMBUS_SMT1 0x0c5a

#define ISMT_DESC_ENTRIES 32 /* number of descritor entries */
#define ISMT_MAX_RETRIES 3   /* number of SMBus retries to attempt */

/* Hardware Descriptor Constants - Control Field */
#define ISMT_DESC_CWRL  0x01    /* Command/Write Length */
#define ISMT_DESC_BLK   0X04    /* Perform Block Transaction */
#define ISMT_DESC_FAIR  0x08    /* Set fairness flag upon successful arbit. */
#define ISMT_DESC_PEC   0x10    /* Packet Error Code */
#define ISMT_DESC_I2C   0x20    /* I2C Enable */
#define ISMT_DESC_INT   0x40    /* Interrupt */
#define ISMT_DESC_SOE   0x80    /* Stop On Error */

/* Hardware Descriptor Constants - Status Field */
#define ISMT_DESC_SCS   0x01    /* Success */
#define ISMT_DESC_DLTO  0x04    /* Data Low Time Out */
#define ISMT_DESC_NAK   0x08    /* NAK Received */
#define ISMT_DESC_CRC   0x10    /* CRC Error */
#define ISMT_DESC_CLTO  0x20    /* Clock Low Time Out */
#define ISMT_DESC_COL   0x40    /* Collisions */
#define ISMT_DESC_LPR   0x80    /* Large Packet Received */

/* Hardware Descriptor Masks */
#define ISMT_DESC_ADDR  0x7f    /* I2C/SMB address mask */
#define ISMT_DESC_RW    0x01    /* Read/Write bit mask */

/* Macros */
#define ISMT_DESC_ADDR_RW(addr, rw) (((addr & ISMT_DESC_ADDR) << 1)	\
				     | (rw & ISMT_DESC_RW))

/* iSMT General Register address offsets (SMBAR + <addr>) */
#define ISMT_GR_GCTRL      0x000 /* General Control */
#define ISMT_GR_SMTICL     0x008 /* SMT Interrupt Cause Location */
#define ISMT_GR_ERRINTMSK  0x010 /* Error Interrupt Mask */
#define ISMT_GR_ERRAERMSK  0x014 /* Error AER Mask */
#define ISMT_GR_ERRSTS     0x018 /* Error Status */
#define ISMT_GR_ERRINFO    0x01c /* Error Information */

/* iSMT Master Registers */
#define ISMT_MSTR_MDBA    0x100  /* Master Descriptor Base Address */
#define ISMT_MSTR_MCTRL   0x108  /* Master Control */
#define ISMT_MSTR_MSTS    0x10c  /* Master Status */
#define ISMT_MSTR_MDS     0x110  /* Master Descriptor Size */
#define ISMT_MSTR_RPOLICY 0x114  /* Retry Policy */

/* iSMT Miscellaneous Registers */
#define ISMT_SPGT  0x300  /* SMBus PHY Global Timing */

/* General Control Register (GCTRL) bit definitions */
#define ISMT_GCTRL_TRST 0x04    /* Target Reset */
#define ISMT_GCTRL_KILL 0x08    /* Kill */
#define ISMT_GCTRL_SRST 0x40    /* Soft Reset */

/* Master Control Register (MCTRL) bit definitions */
#define ISMT_MCTRL_SS    0x01       /* Start/Stop */
#define ISMT_MCTRL_MEIE  0x10       /* Master Error Interrupt Enable */
#define ISMT_MCTRL_FMHP  0x00ff0000 /* Firmware Master Head Pointer (FMHP) */

/* Master Status Register (MSTS) bit definitions */
#define ISMT_MSTS_HMTP  0xff0000 /* HW Master Tail Pointer (HMTP) */
#define ISMT_MSTS_MIS   0x20     /* Master Interrupt Status (MIS) */
#define ISMT_MSTS_MEIS  0x10     /* Master Error Interrupt Status (MEIS) */
#define ISMT_MSTS_IP    0x01     /* In Progress */

/* Master Descriptor Size (MDS) bit definitions */
#define ISMT_MDS_MDS  0xFF /* Master Descriptor Size mask (MDS) */

/* SMBus PHY Global Timing Register (SPGT) bit definitions */
#define ISMT_SPGT_SPD     0xc0000000   /* SMBus Speed mask */
#define ISMT_SPGT_SPD_80K (0x01 << 30) /* 80 KHz */

/* MSI Control Register (MSICTL) bit definitions */
#define ISMT_MSICTL_MSIE 0x01 /* MSI Enable */

/* iSMT Hardware Descriptor */
struct ismt_desc {
	u8 tgtaddr_rw; /* target address & r/w bit */
	u8 wr_len_cmd; /* write length in bytes or a command */
	u8 rd_len; /* read length */
	u8 control; /* control bits */
	u8 status; /* status bits */
	u8 retry; /* collision retry and retry count */
	u8 rxbytes; /* received bytes */
	u8 txbytes; /* transmitted bytes */
	u32 dptr_low; /* lower 32 bit of the data pointer */
	u32 dptr_high; /* upper 32 bit of the data pointer */
};

struct ismt_priv {
	struct i2c_adapter adapter;
	void *smba; /* PCI BAR */
	struct pci_dev *pci_dev;
	struct ismt_ring_ent **ring; /* housekeeping struct pointer */
	struct ismt_desc *hw; /* virtual base address of the descriptor */
	dma_addr_t io_rng_dma; /* hardware base address of the descriptor */
	int entries; /* number of descriptor entries */
	u8 head; /* ring buffer head pointer */
	u8 tail; /* ring buffer tail pointer */
	struct completion cmp; /* interrupt completion */
};

#endif
