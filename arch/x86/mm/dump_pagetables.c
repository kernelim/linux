/*
 * Debug helper to dump the current kernel pagetables of the system
 * so that we can see what the various memory ranges are set to.
 *
 * (C) Copyright 2008 Intel Corporation
 *
 * Author: Arjan van de Ven <arjan@linux.intel.com>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; version 2
 * of the License.
 */

#include <linux/debugfs.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/seq_file.h>

#include <asm/pgtable.h>
#include <asm/io.h>

/*
 * The dumper groups pagetable entries of the same type into one, and for
 * that it needs to keep some state when walking, and flush this state
 * when a "break" in the continuity is found.
 */
struct pg_state {
	int level;
	pgprot_t current_prot;
	unsigned long start_address;
	unsigned long current_address;
	const struct addr_marker *marker;
};

struct addr_marker {
	unsigned long start_address;
	const char *name;
};

/* Address space markers hints */
static struct addr_marker address_markers[] = {
	{ 0, "User Space" },
#ifdef CONFIG_X86_64
	{ 0x8000000000000000UL, "Kernel Space" },
	{ PAGE_OFFSET,		"Low Kernel Mapping" },
	{ VMALLOC_START,        "vmalloc() Area" },
	{ VMEMMAP_START,        "Vmemmap" },
	{ __START_KERNEL_map,   "High Kernel Mapping" },
	{ MODULES_VADDR,        "Modules" },
	{ MODULES_END,          "End Modules" },
#else
	{ PAGE_OFFSET,          "Kernel Mapping" },
	{ 0/* VMALLOC_START */, "vmalloc() Area" },
	{ 0/*VMALLOC_END*/,     "vmalloc() End" },
# ifdef CONFIG_HIGHMEM
	{ 0/*PKMAP_BASE*/,      "Persisent kmap() Area" },
# endif
	{ 0/*FIXADDR_START*/,   "Fixmap Area" },
#endif
	{ -1, NULL }		/* End of list */
};

/* Multipliers for offsets within the PTEs */
#define PTE_LEVEL_MULT (PAGE_SIZE)
#define PMD_LEVEL_MULT (PTRS_PER_PTE * PTE_LEVEL_MULT)
#define PUD_LEVEL_MULT (PTRS_PER_PMD * PMD_LEVEL_MULT)
#define PGD_LEVEL_MULT (PTRS_PER_PUD * PUD_LEVEL_MULT)

#define PGPROT_HIMEM	((pgprotval_t)-1)
#ifdef CONFIG_HIGHMEM
/*
 * Return true if a kernel page table entry point to an address in the
 * high memory area.
 */
static inline bool page_in_himem(pmdval_t val)
{
	return ((val & PTE_PFN_MASK) + (pteval_t)PAGE_OFFSET) >=
			VMALLOC_START;
}
#else
static inline bool page_in_himem(pmdval_t val)
{
	return false;
}
#endif

/*
 * Print a readable form of a pgprot_t to the seq_file
 */
static void printk_prot(struct seq_file *m, pgprot_t prot, int level)
{
	pgprotval_t pr = pgprot_val(prot);
	static const char * const level_name[] =
		{ "cr3", "pgd", "pud", "pmd", "pte" };

	if (!pgprot_val(prot)) {
		/* Not present */
		seq_printf(m, "                          ");
	} else if (pgprot_val(prot) == PGPROT_HIMEM) {
		/* In high memory */
		seq_printf(m, "         [HIMEM]          ");
	} else {
		if (pr & _PAGE_USER)
			seq_printf(m, "USR ");
		else
			seq_printf(m, "    ");
		if (pr & _PAGE_RW)
			seq_printf(m, "RW ");
		else
			seq_printf(m, "ro ");
		if (pr & _PAGE_PWT)
			seq_printf(m, "PWT ");
		else
			seq_printf(m, "    ");
		if (pr & _PAGE_PCD)
			seq_printf(m, "PCD ");
		else
			seq_printf(m, "    ");

		/* Bit 9 has a different meaning on level 3 vs 4 */
		if (level <= 3) {
			if (pr & _PAGE_PSE)
				seq_printf(m, "PSE ");
			else
				seq_printf(m, "    ");
		} else {
			if (pr & _PAGE_PAT)
				seq_printf(m, "pat ");
			else
				seq_printf(m, "    ");
		}
		if (pr & _PAGE_GLOBAL)
			seq_printf(m, "GLB ");
		else
			seq_printf(m, "    ");
		if (pr & _PAGE_NX)
			seq_printf(m, "NX ");
		else
			seq_printf(m, "x  ");
	}
	seq_printf(m, "%s\n", level_name[level]);
}

/*
 * On 64 bits, sign-extend the 48 bit address to 64 bit
 */
static unsigned long normalize_addr(unsigned long u)
{
#ifdef CONFIG_X86_64
	return (signed long)(u << 16) >> 16;
#else
	return u;
#endif
}

/*
 * This function gets called on a break in a continuous series
 * of PTE entries; the next one is different so we need to
 * print what we collected so far.
 */
static void note_page(struct seq_file *m, struct pg_state *st,
		      pgprot_t new_prot, int level)
{
	pgprotval_t prot, cur;
	static const char units[] = "KMGTPE";

	/*
	 * If we have a "break" in the series, we need to flush the state that
	 * we have now. "break" is either changing perms, levels or
	 * address space marker.
	 */
	prot = pgprot_val(new_prot) & PTE_FLAGS_MASK;
	cur = pgprot_val(st->current_prot) & PTE_FLAGS_MASK;

	if (!st->level) {
		/* First entry */
		st->current_prot = new_prot;
		st->level = level;
		st->marker = address_markers;
		seq_printf(m, "---[ %s ]---\n", st->marker->name);
	} else if (prot != cur || level != st->level ||
		   st->current_address >= st->marker[1].start_address) {
		const char *unit = units;
		unsigned long delta;
		int width = sizeof(unsigned long) * 2;

		/*
		 * Now print the actual finished series
		 */
		seq_printf(m, "0x%0*lx-0x%0*lx   ",
			   width, st->start_address,
			   width, st->current_address);

		delta = (st->current_address - st->start_address) >> 10;
		while (!(delta & 1023) && unit[1]) {
			delta >>= 10;
			unit++;
		}
		seq_printf(m, "%9lu%c ", delta, *unit);
		printk_prot(m, st->current_prot, st->level);

		/*
		 * We print markers for special areas of address space,
		 * such as the start of vmalloc space etc.
		 * This helps in the interpretation.
		 */
		if (st->current_address >= st->marker[1].start_address) {
			st->marker++;
			seq_printf(m, "---[ %s ]---\n", st->marker->name);
		}

		st->start_address = st->current_address;
		st->current_prot = new_prot;
		st->level = level;
	}
}

static void walk_pte_level(struct seq_file *m, struct pg_state *st, pmd_t addr,
							unsigned long P)
{
	int i;
	pte_t *start;

	if (page_in_himem(pmd_val(addr))) {
		note_page(m, st, __pgprot(PGPROT_HIMEM), 3);
		return;
	}
	start = (pte_t *) pmd_page_vaddr(addr);
	for (i = 0; i < PTRS_PER_PTE; i++) {
		pgprot_t prot = pte_pgprot(*start);

		st->current_address = normalize_addr(P + i * PTE_LEVEL_MULT);
		note_page(m, st, prot, 4);
		start++;
	}
}

#if PTRS_PER_PMD > 1

static void walk_pmd_level(struct seq_file *m, struct pg_state *st, pud_t addr,
							unsigned long P)
{
	int i;
	pmd_t *start;

	if (page_in_himem((pmdval_t)pud_val(addr))) {
		note_page(m, st, __pgprot(PGPROT_HIMEM), 2);
		return;
	}
	start = (pmd_t *) pud_page_vaddr(addr);
	for (i = 0; i < PTRS_PER_PMD; i++) {
		st->current_address = normalize_addr(P + i * PMD_LEVEL_MULT);
		if (!pmd_none(*start)) {
			pgprotval_t prot = pmd_val(*start) & PTE_FLAGS_MASK;

			if (pmd_large(*start) || !pmd_present(*start))
				note_page(m, st, __pgprot(prot), 3);
			else
				walk_pte_level(m, st, *start,
					       P + i * PMD_LEVEL_MULT);
		} else
			note_page(m, st, __pgprot(0), 3);
		start++;
	}
}

#else
#define walk_pmd_level(m,s,a,p) walk_pte_level(m,s,__pmd(pud_val(a)),p)
#define pud_large(a) pmd_large(__pmd(pud_val(a)))
#define pud_none(a)  pmd_none(__pmd(pud_val(a)))
#endif

#if PTRS_PER_PUD > 1

static void walk_pud_level(struct seq_file *m, struct pg_state *st, pgd_t addr,
							unsigned long P)
{
	int i;
	pud_t *start;

	start = (pud_t *) pgd_page_vaddr(addr);

	for (i = 0; i < PTRS_PER_PUD; i++) {
		st->current_address = normalize_addr(P + i * PUD_LEVEL_MULT);
		if (!pud_none(*start)) {
			pgprotval_t prot = pud_val(*start) & PTE_FLAGS_MASK;

			if (pud_large(*start) || !pud_present(*start))
				note_page(m, st, __pgprot(prot), 2);
			else
				walk_pmd_level(m, st, *start,
					       P + i * PUD_LEVEL_MULT);
		} else
			note_page(m, st, __pgprot(0), 2);

		start++;
	}
}

#else
#define walk_pud_level(m,s,a,p) walk_pmd_level(m,s,__pud(pgd_val(a)),p)
#define pgd_large(a) pud_large(__pud(pgd_val(a)))
#define pgd_none(a)  pud_none(__pud(pgd_val(a)))
#endif

static void walk_pgd_level(struct seq_file *m, pgd_t *pgd)
{
	int i;
	struct pg_state st;

	if (!pgd) {
#ifdef CONFIG_X86_64
		pgd = (pgd_t *) &init_level4_pgt;
#else
		pgd = swapper_pg_dir;
#endif
	}

	memset(&st, 0, sizeof(st));

	for (i = 0; i < PTRS_PER_PGD; i++) {
		st.current_address = normalize_addr(i * PGD_LEVEL_MULT);
		if (!pgd_none(*pgd)) {
			pgprotval_t prot = pgd_val(*pgd) & PTE_FLAGS_MASK;

			if (pgd_large(*pgd) || !pgd_present(*pgd))
				note_page(m, &st, __pgprot(prot), 1);
			else
				walk_pud_level(m, &st, *pgd,
					       i * PGD_LEVEL_MULT);
		} else
			note_page(m, &st, __pgprot(0), 1);

		pgd++;
	}

	/* Flush out the last page */
	st.current_address = normalize_addr(PTRS_PER_PGD*PGD_LEVEL_MULT);
	note_page(m, &st, __pgprot(0), 0);
}

static int ptdump_show(struct seq_file *m, void *v)
{
	walk_pgd_level(m, NULL);
	return 0;
}

static int ptdump_open(struct inode *inode, struct file *filp)
{
	return single_open(filp, ptdump_show, NULL);
}

static const struct file_operations ptdump_fops = {
	.open		= ptdump_open,
	.read		= seq_read,
	.llseek		= seq_lseek,
	.release	= single_release,
};

static int ptdump_show_curknl(struct seq_file *m, void *v)
{
	if (current->mm->pgd) {
		down_read(&current->mm->mmap_sem);
		walk_pgd_level(m, current->mm->pgd);
		up_read(&current->mm->mmap_sem);
	}
	return 0;
}

static int ptdump_open_curknl(struct inode *inode, struct file *filp)
{
	return single_open(filp, ptdump_show_curknl, NULL);
}

static const struct file_operations ptdump_curknl_fops = {
	.owner		= THIS_MODULE,
	.open		= ptdump_open_curknl,
	.read		= seq_read,
	.llseek		= seq_lseek,
	.release	= single_release,
};

#ifdef CONFIG_PAGE_TABLE_ISOLATION
static int ptdump_show_curusr(struct seq_file *m, void *v)
{
	if (current->mm->pgd) {
		down_read(&current->mm->mmap_sem);
		walk_pgd_level(m, kernel_to_shadow_pgdp(current->mm->pgd));
		up_read(&current->mm->mmap_sem);
	}
	return 0;
}

static int ptdump_open_curusr(struct inode *inode, struct file *filp)
{
	return single_open(filp, ptdump_show_curusr, NULL);
}

static const struct file_operations ptdump_curusr_fops = {
	.owner		= THIS_MODULE,
	.open		= ptdump_open_curusr,
	.read		= seq_read,
	.llseek		= seq_lseek,
	.release	= single_release,
};
#endif

/*
 * Check to see if L1 terminal fault is properly mitigated.
 */
static int ptcheck_show_l1tf(struct seq_file *m, void *v)
{
	u32 *page0;
	int i, j;
	bool print_page0 = false;

	/*
	 * Check the content of physical page 0 as the content of this
	 * page may be exposed.
	 *
	 * Page 0 is marked as "BIOS data page" and is not used by the kernel.
	 * The first 1k is Real Mode interrupt vector table. The next 256
	 * bytes is BIOS data area. The rests may probably be used in the
	 * bootup process.
	 */
	page0 = (u32 *)phys_to_virt(0);
	for (i = 0; i < PAGE_SIZE/sizeof(u32); i += 8) {
		for (j = 0; j < 8; j++)
			if (page0[i + j])
				break;
		if (j == 8)
			continue;

		if (!print_page0) {
			print_page0 = true;
			seq_printf(m, "Page 0 non-zero content\n"
				      "-----------------------\n");
		}

		/*
		 * Print out the line with non-zero values.
		 */
		seq_printf(m, "%04x:", i * (int)sizeof(u32));
		for (j = 0; j < 8; j++)
			seq_printf(m, " %08x", page0[i + j]);
		seq_printf(m, "\n");
	}
	if (print_page0)
		seq_printf(m, "-----------------------\n");

	return 0;
}

static int ptcheck_open_l1tf(struct inode *inode, struct file *filp)
{
	return single_open(filp, ptcheck_show_l1tf, NULL);
}

static const struct file_operations ptcheck_l1tf_fops = {
	.owner		= THIS_MODULE,
	.open		= ptcheck_open_l1tf,
	.read		= seq_read,
	.llseek		= seq_lseek,
	.release	= single_release,
};

static int pt_dump_init(void)
{
static struct dentry *dir, *pe_knl, *pe_curknl, *pe_l1tf;
#ifdef CONFIG_PAGE_TABLE_ISOLATION
static struct dentry *pe_curusr;
#endif

#ifdef CONFIG_X86_32
	/* Not a compile-time constant on x86-32 */
	address_markers[2].start_address = VMALLOC_START;
	address_markers[3].start_address = VMALLOC_END;
# ifdef CONFIG_HIGHMEM
	address_markers[4].start_address = PKMAP_BASE;
	address_markers[5].start_address = FIXADDR_START;
# else
	address_markers[4].start_address = FIXADDR_START;
# endif
#endif

	dir = debugfs_create_dir("page_tables", NULL);
	if (!dir)
		return -ENOMEM;

	pe_knl = debugfs_create_file("kernel", 0400, dir, NULL, &ptdump_fops);
	if (!pe_knl)
		goto err;

	pe_curknl =  debugfs_create_file("current_kernel", 0400,
					 dir, NULL, &ptdump_curknl_fops);
	if (!pe_curknl)
		goto err;

#ifdef CONFIG_PAGE_TABLE_ISOLATION
	pe_curusr =  debugfs_create_file("current_user", 0400,
					 dir, NULL, &ptdump_curusr_fops);
	if (!pe_curusr)
		goto err;
#endif

	pe_l1tf = debugfs_create_file("check_l1tf", 0400,
				      dir, NULL, &ptcheck_l1tf_fops);

	return 0;
err:
	debugfs_remove_recursive(dir);
	return -ENOMEM;
}

__initcall(pt_dump_init);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Arjan van de Ven <arjan@linux.intel.com>");
MODULE_DESCRIPTION("Kernel debugging helper that dumps pagetables");
