/*
 * This file contains the routines for handling the MMU on those
 * PowerPC implementations where the MMU substantially follows the
 * architecture specification.  This includes the 6xx, 7xx, 7xxx,
 * and 8260 implementations but excludes the 8xx and 4xx.
 *  -- paulus
 *
 *  Derived from arch/ppc/mm/init.c:
 *    Copyright (C) 1995-1996 Gary Thomas (gdt@linuxppc.org)
 *
 *  Modifications by Paul Mackerras (PowerMac) (paulus@cs.anu.edu.au)
 *  and Cort Dougan (PReP) (cort@cs.nmt.edu)
 *    Copyright (C) 1996 Paul Mackerras
 *
 *  Derived from "arch/i386/mm/init.c"
 *    Copyright (C) 1991, 1992, 1993, 1994  Linus Torvalds
 *
 *  This program is free software; you can redistribute it and/or
 *  modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; either version
 *  2 of the License, or (at your option) any later version.
 *
 */

#include <linux/kernel.h>
#include <linux/mm.h>
#include <linux/init.h>
#include <linux/highmem.h>
#include <linux/memblock.h>

#include <asm/prom.h>
#include <asm/mmu.h>
#include <asm/machdep.h>

#include <mm/mmu_decl.h>

struct hash_pte *Hash, *Hash_end;
unsigned long Hash_size, Hash_mask;
unsigned long _SDR1;

struct ppc_bat BATS[8][2];	/* 8 pairs of IBAT, DBAT */

struct batrange {		/* stores address ranges mapped by BATs */
	unsigned long start;
	unsigned long limit;
	phys_addr_t phys;
} bat_addrs[8];

/*
 * Return PA for this VA if it is mapped by a BAT, or 0
 */
phys_addr_t v_block_mapped(unsigned long va)
{
	int b;
	for (b = 0; b < 4; ++b)
		if (va >= bat_addrs[b].start && va < bat_addrs[b].limit)
			return bat_addrs[b].phys + (va - bat_addrs[b].start);
	return 0;
}

/*
 * Return VA for a given PA or 0 if not mapped
 */
unsigned long p_block_mapped(phys_addr_t pa)
{
	int b;
	for (b = 0; b < 4; ++b)
		if (pa >= bat_addrs[b].phys
	    	    && pa < (bat_addrs[b].limit-bat_addrs[b].start)
		              +bat_addrs[b].phys)
			return bat_addrs[b].start+(pa-bat_addrs[b].phys);
	return 0;
}

unsigned long __init mmu_mapin_ram(unsigned long top)
{
	unsigned long tot, bl, done;
	unsigned long max_size = (256<<20);

	if (__map_without_bats) {
		printk(KERN_DEBUG "RAM mapped without BATs\n");
		return 0;
	}

	/* Set up BAT2 and if necessary BAT3 to cover RAM. */

	/* Make sure we don't map a block larger than the
	   smallest alignment of the physical address. */
	tot = top;
	for (bl = 128<<10; bl < max_size; bl <<= 1) {
		if (bl * 2 > tot)
			break;
	}

	setbat(2, PAGE_OFFSET, 0, bl, PAGE_KERNEL_X);
	done = (unsigned long)bat_addrs[2].limit - PAGE_OFFSET + 1;
	if ((done < tot) && !bat_addrs[3].limit) {
		/* use BAT3 to cover a bit more */
		tot -= done;
		for (bl = 128<<10; bl < max_size; bl <<= 1)
			if (bl * 2 > tot)
				break;
		setbat(3, PAGE_OFFSET+done, done, bl, PAGE_KERNEL_X);
		done = (unsigned long)bat_addrs[3].limit - PAGE_OFFSET + 1;
	}

	return done;
}

/*
 * Set up one of the I/D BAT (block address translation) register pairs.
 * The parameters are not checked; in particular size must be a power
 * of 2 between 128k and 256M.
 */
void __init setbat(int index, unsigned long virt, phys_addr_t phys,
		   unsigned int size, pgprot_t prot)
{
	unsigned int bl;
	int wimgxpp;
	struct ppc_bat *bat = BATS[index];
	unsigned long flags = pgprot_val(prot);

	if ((flags & _PAGE_NO_CACHE) ||
	    (cpu_has_feature(CPU_FTR_NEED_COHERENT) == 0))
		flags &= ~_PAGE_COHERENT;

	bl = (size >> 17) - 1;
	if (PVR_VER(mfspr(SPRN_PVR)) != 1) {
		/* 603, 604, etc. */
		/* Do DBAT first */
		wimgxpp = flags & (_PAGE_WRITETHRU | _PAGE_NO_CACHE
				   | _PAGE_COHERENT | _PAGE_GUARDED);
		wimgxpp |= (flags & _PAGE_RW)? BPP_RW: BPP_RX;
		bat[1].batu = virt | (bl << 2) | 2; /* Vs=1, Vp=0 */
		bat[1].batl = BAT_PHYS_ADDR(phys) | wimgxpp;
		if (flags & _PAGE_USER)
			bat[1].batu |= 1; 	/* Vp = 1 */
		if (flags & _PAGE_GUARDED) {
			/* G bit must be zero in IBATs */
			bat[0].batu = bat[0].batl = 0;
		} else {
			/* make IBAT same as DBAT */
			bat[0] = bat[1];
		}
	} else {
		/* 601 cpu */
		if (bl > BL_8M)
			bl = BL_8M;
		wimgxpp = flags & (_PAGE_WRITETHRU | _PAGE_NO_CACHE
				   | _PAGE_COHERENT);
		wimgxpp |= (flags & _PAGE_RW)?
			((flags & _PAGE_USER)? PP_RWRW: PP_RWXX): PP_RXRX;
		bat->batu = virt | wimgxpp | 4;	/* Ks=0, Ku=1 */
		bat->batl = phys | bl | 0x40;	/* V=1 */
	}

	bat_addrs[index].start = virt;
	bat_addrs[index].limit = virt + ((bl + 1) << 17) - 1;
	bat_addrs[index].phys = phys;
}

/*
 * Preload a translation in the hash table
 */
void hash_preload(struct mm_struct *mm, unsigned long ea,
		  bool is_exec, unsigned long trap)
{
	pmd_t *pmd;

	if (!Hash)
		return;
	pmd = pmd_offset(pud_offset(pgd_offset(mm, ea), ea), ea);
	if (!pmd_none(*pmd))
		add_hash_page(mm->context.id, ea, pmd_val(*pmd));
}

/*
 * This is called at the end of handling a user page fault, when the
 * fault has been handled by updating a PTE in the linux page tables.
 * We use it to preload an HPTE into the hash table corresponding to
 * the updated linux PTE.
 *
 * This must always be called with the pte lock held.
 */
void update_mmu_cache(struct vm_area_struct *vma, unsigned long address,
		      pte_t *ptep)
{
	/*
	 * We don't need to worry about _PAGE_PRESENT here because we are
	 * called with either mm->page_table_lock held or ptl lock held
	 */
	unsigned long trap;
	bool is_exec;

	/* We only want HPTEs for linux PTEs that have _PAGE_ACCESSED set */
	if (!pte_young(*ptep) || address >= TASK_SIZE)
		return;

	/*
	 * We try to figure out if we are coming from an instruction
	 * access fault and pass that down to __hash_page so we avoid
	 * double-faulting on execution of fresh text. We have to test
	 * for regs NULL since init will get here first thing at boot.
	 *
	 * We also avoid filling the hash if not coming from a fault.
	 */

	trap = current->thread.regs ? TRAP(current->thread.regs) : 0UL;
	switch (trap) {
	case 0x300:
		is_exec = false;
		break;
	case 0x400:
		is_exec = true;
		break;
	default:
		return;
	}

	hash_preload(vma->vm_mm, address, is_exec, trap);
}

/*
 * Initialize the hash table and patch the instructions in hashtable.S.
 */
void __init MMU_init_hw(void)
{
	unsigned int hmask, mb, mb2;
	unsigned int n_hpteg, lg_n_hpteg;

	extern unsigned int hash_page_patch_A[];
	extern unsigned int hash_page_patch_B[], hash_page_patch_C[];
	extern unsigned int hash_page[];
	extern unsigned int flush_hash_patch_A[], flush_hash_patch_B[];

	if (!mmu_has_feature(MMU_FTR_HPTE_TABLE)) {
		/*
		 * Put a blr (procedure return) instruction at the
		 * start of hash_page, since we can still get DSI
		 * exceptions on a 603.
		 */
		hash_page[0] = 0x4e800020;
		flush_icache_range((unsigned long) &hash_page[0],
				   (unsigned long) &hash_page[1]);
		return;
	}

	if ( ppc_md.progress ) ppc_md.progress("hash:enter", 0x105);

#define LG_HPTEG_SIZE	6		/* 64 bytes per HPTEG */
#define SDR1_LOW_BITS	((n_hpteg - 1) >> 10)
#define MIN_N_HPTEG	1024		/* min 64kB hash table */

	/*
	 * Allow 1 HPTE (1/8 HPTEG) for each page of memory.
	 * This is less than the recommended amount, but then
	 * Linux ain't AIX.
	 */
	n_hpteg = total_memory / (PAGE_SIZE * 8);
	if (n_hpteg < MIN_N_HPTEG)
		n_hpteg = MIN_N_HPTEG;
	lg_n_hpteg = __ilog2(n_hpteg);
	if (n_hpteg & (n_hpteg - 1)) {
		++lg_n_hpteg;		/* round up if not power of 2 */
		n_hpteg = 1 << lg_n_hpteg;
	}
	Hash_size = n_hpteg << LG_HPTEG_SIZE;

	/*
	 * Find some memory for the hash table.
	 */
	if ( ppc_md.progress ) ppc_md.progress("hash:find piece", 0x322);
	Hash = __va(memblock_phys_alloc(Hash_size, Hash_size));
	memset(Hash, 0, Hash_size);
	_SDR1 = __pa(Hash) | SDR1_LOW_BITS;

	Hash_end = (struct hash_pte *) ((unsigned long)Hash + Hash_size);

	printk("Total memory = %lldMB; using %ldkB for hash table (at %p)\n",
	       (unsigned long long)(total_memory >> 20), Hash_size >> 10, Hash);


	/*
	 * Patch up the instructions in hashtable.S:create_hpte
	 */
	if ( ppc_md.progress ) ppc_md.progress("hash:patch", 0x345);
	Hash_mask = n_hpteg - 1;
	hmask = Hash_mask >> (16 - LG_HPTEG_SIZE);
	mb2 = mb = 32 - LG_HPTEG_SIZE - lg_n_hpteg;
	if (lg_n_hpteg > 16)
		mb2 = 16 - LG_HPTEG_SIZE;

	hash_page_patch_A[0] = (hash_page_patch_A[0] & ~0xffff)
		| ((unsigned int)(Hash) >> 16);
	hash_page_patch_A[1] = (hash_page_patch_A[1] & ~0x7c0) | (mb << 6);
	hash_page_patch_A[2] = (hash_page_patch_A[2] & ~0x7c0) | (mb2 << 6);
	hash_page_patch_B[0] = (hash_page_patch_B[0] & ~0xffff) | hmask;
	hash_page_patch_C[0] = (hash_page_patch_C[0] & ~0xffff) | hmask;

	/*
	 * Ensure that the locations we've patched have been written
	 * out from the data cache and invalidated in the instruction
	 * cache, on those machines with split caches.
	 */
	flush_icache_range((unsigned long) &hash_page_patch_A[0],
			   (unsigned long) &hash_page_patch_C[1]);

	/*
	 * Patch up the instructions in hashtable.S:flush_hash_page
	 */
	flush_hash_patch_A[0] = (flush_hash_patch_A[0] & ~0xffff)
		| ((unsigned int)(Hash) >> 16);
	flush_hash_patch_A[1] = (flush_hash_patch_A[1] & ~0x7c0) | (mb << 6);
	flush_hash_patch_A[2] = (flush_hash_patch_A[2] & ~0x7c0) | (mb2 << 6);
	flush_hash_patch_B[0] = (flush_hash_patch_B[0] & ~0xffff) | hmask;
	flush_icache_range((unsigned long) &flush_hash_patch_A[0],
			   (unsigned long) &flush_hash_patch_B[1]);

	if ( ppc_md.progress ) ppc_md.progress("hash:done", 0x205);
}

void setup_initial_memory_limit(phys_addr_t first_memblock_base,
				phys_addr_t first_memblock_size)
{
	/* We don't currently support the first MEMBLOCK not mapping 0
	 * physical on those processors
	 */
	BUG_ON(first_memblock_base != 0);

	/* 601 can only access 16MB at the moment */
	if (PVR_VER(mfspr(SPRN_PVR)) == 1)
		memblock_set_current_limit(min_t(u64, first_memblock_size, 0x01000000));
	else /* Anything else has 256M mapped */
		memblock_set_current_limit(min_t(u64, first_memblock_size, 0x10000000));
}
