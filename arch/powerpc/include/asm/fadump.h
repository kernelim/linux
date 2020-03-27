/*
 * Firmware Assisted dump header file.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * Copyright 2011 IBM Corporation
 * Author: Mahesh Salgaonkar <mahesh@linux.vnet.ibm.com>
 */

#ifndef _ASM_POWERPC_FADUMP_H
#define _ASM_POWERPC_FADUMP_H

#ifdef CONFIG_FA_DUMP

extern int crashing_cpu;

extern int is_fadump_memory_area(u64 addr, ulong size);
extern int setup_fadump(void);
extern int is_fadump_active(void);
extern int should_fadump_crash(void);
extern void crash_fadump(struct pt_regs *, const char *);
extern void fadump_cleanup(void);

#else	/* CONFIG_FA_DUMP */
static inline int is_fadump_active(void) { return 0; }
static inline int should_fadump_crash(void) { return 0; }
static inline void crash_fadump(struct pt_regs *regs, const char *str) { }
static inline void fadump_cleanup(void) { }
#endif /* !CONFIG_FA_DUMP */

#if defined(CONFIG_FA_DUMP) || defined(CONFIG_PRESERVE_FA_DUMP)
extern int early_init_dt_scan_fw_dump(unsigned long node, const char *uname,
				      int depth, void *data);
extern int fadump_reserve_mem(void);
#endif
#endif /* _ASM_POWERPC_FADUMP_H */
