/* SPDX-License-Identifier: GPL-2.0 */
#ifndef BOOT_COMPRESSED_EBOOT_H
#define BOOT_COMPRESSED_EBOOT_H

#define SEG_TYPE_DATA		(0 << 3)
#define SEG_TYPE_READ_WRITE	(1 << 1)
#define SEG_TYPE_CODE		(1 << 3)
#define SEG_TYPE_EXEC_READ	(1 << 1)
#define SEG_TYPE_TSS		((1 << 3) | (1 << 0))
#define SEG_OP_SIZE_32BIT	(1 << 0)
#define SEG_GRANULARITY_4KB	(1 << 0)

#define DESC_TYPE_CODE_DATA	(1 << 0)

typedef enum {
	EfiGcdMemoryTypeNonExistent,
	EfiGcdMemoryTypeReserved,
	EfiGcdMemoryTypeSystemMemory,
	EfiGcdMemoryTypeMemoryMappedIo,
	EfiGcdMemoryTypePersistent,
	EfiGcdMemoryTypeMoreReliable,
	EfiGcdMemoryTypeMaximum
} efi_gcd_memory_type_t;

typedef struct {
	efi_physical_addr_t base_address;
	u64 length;
	u64 capabilities;
	u64 attributes;
	efi_gcd_memory_type_t gcd_memory_type;
	void *image_handle;
	void *device_handle;
} efi_gcd_memory_space_desc_t;

/*
 * EFI DXE Services table
 */
union efi_dxe_services_table {
	struct {
		efi_table_hdr_t hdr;
		void *add_memory_space;
		void *allocate_memory_space;
		void *free_memory_space;
		void *remove_memory_space;
		efi_status_t (__efiapi *get_memory_space_descriptor)(efi_physical_addr_t,
								     efi_gcd_memory_space_desc_t *);
		efi_status_t (__efiapi *set_memory_space_attributes)(efi_physical_addr_t,
								     u64, u64);
		void *get_memory_space_map;
		void *add_io_space;
		void *allocate_io_space;
		void *free_io_space;
		void *remove_io_space;
		void *get_io_space_descriptor;
		void *get_io_space_map;
		void *dispatch;
		void *schedule;
		void *trust;
		void *process_firmware_volume;
		void *set_memory_space_capabilities;
	};
	struct {
		efi_table_hdr_t hdr;
		u32 add_memory_space;
		u32 allocate_memory_space;
		u32 free_memory_space;
		u32 remove_memory_space;
		u32 get_memory_space_descriptor;
		u32 set_memory_space_attributes;
		u32 get_memory_space_map;
		u32 add_io_space;
		u32 allocate_io_space;
		u32 free_io_space;
		u32 remove_io_space;
		u32 get_io_space_descriptor;
		u32 get_io_space_map;
		u32 dispatch;
		u32 schedule;
		u32 trust;
		u32 process_firmware_volume;
		u32 set_memory_space_capabilities;
	} mixed_mode;
};

typedef union efi_dxe_services_table efi_dxe_services_table_t;

typedef union efi_memory_attribute_protocol efi_memory_attribute_protocol_t;

union efi_memory_attribute_protocol {
	struct {
		efi_status_t (__efiapi *get_memory_attributes)(
			efi_memory_attribute_protocol_t *, efi_physical_addr_t, u64, u64 *);

		efi_status_t (__efiapi *set_memory_attributes)(
			efi_memory_attribute_protocol_t *, efi_physical_addr_t, u64, u64);

		efi_status_t (__efiapi *clear_memory_attributes)(
			efi_memory_attribute_protocol_t *, efi_physical_addr_t, u64, u64);
	};
	struct {
		u32 get_memory_attributes;
		u32 set_memory_attributes;
		u32 clear_memory_attributes;
	} mixed_mode;
};

typedef struct {
	u32 get_mode;
	u32 set_mode;
	u32 blt;
} efi_uga_draw_protocol_32_t;

typedef struct {
	u64 get_mode;
	u64 set_mode;
	u64 blt;
} efi_uga_draw_protocol_64_t;

typedef union {
	struct {
		void *get_mode;
		void *set_mode;
		void *blt;
	};
	struct {
		u32 get_mode;
		u32 set_mode;
		u32 blt;
	} mixed_mode;
} efi_uga_draw_protocol_t;

void *get_efi_config_table(efi_system_table_t *sys_table, efi_guid_t guid);

#endif /* BOOT_COMPRESSED_EBOOT_H */
