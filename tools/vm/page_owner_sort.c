// SPDX-License-Identifier: GPL-2.0
/*
 * User-space helper to sort the output of /sys/kernel/debug/page_owner
 *
 * Example use:
 * cat /sys/kernel/debug/page_owner > page_owner_full.txt
 * ./page_owner_sort page_owner_full.txt sorted_page_owner.txt
 *
 * See Documentation/vm/page_owner.rst
*/

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <regex.h>

struct block_list {
	char *txt;
	int len;
	int num;
};


static regex_t ts_nsec_pattern;
static struct block_list *list;
static int list_size;
static int max_size;

struct block_list *block_head;

int read_block(char *buf, int buf_size, FILE *fin)
{
	char *curr = buf, *const buf_end = buf + buf_size;

	while (buf_end - curr > 1 && fgets(curr, buf_end - curr, fin)) {
		if (*curr == '\n') /* empty line */
			return curr - buf;
		if (!strncmp(curr, "PFN", 3))
			continue;
		curr += strlen(curr);
	}

	return -1; /* EOF or no space left in buf. */
}

static int compare_txt(const void *p1, const void *p2)
{
	const struct block_list *l1 = p1, *l2 = p2;

	return strcmp(l1->txt, l2->txt);
}

static int compare_num(const void *p1, const void *p2)
{
	const struct block_list *l1 = p1, *l2 = p2;

	return l2->num - l1->num;
}

static int remove_pattern(regex_t *pattern, char *buf, int len)
{
	regmatch_t pmatch[2];
	int err;

	err = regexec(pattern, buf, 2, pmatch, REG_NOTBOL);
	if (err != 0 || pmatch[1].rm_so == -1)
	return len;

	memcpy(buf + pmatch[1].rm_so,
		buf + pmatch[1].rm_eo, len - pmatch[1].rm_eo);

	return len - (pmatch[1].rm_eo - pmatch[1].rm_so);
}

static void check_regcomp(regex_t *pattern, const char *regex)
{
	int err;

	err = regcomp(pattern, regex, REG_EXTENDED | REG_NEWLINE);
	if (err != 0 || pattern->re_nsub != 1) {
		printf("Invalid pattern %s code %d\n", regex, err);
		exit(1);
	}
}

static void add_list(char *buf, int len)
{
	if (list_size == max_size) {
		printf("max_size too small??\n");
		exit(1);
	}
	list[list_size].txt = malloc(len+1);
	list[list_size].num = 1;
	memcpy(list[list_size].txt, buf, len);
	len = remove_pattern(&ts_nsec_pattern, list[list_size].txt, len);
	list[list_size].len = len;
	list[list_size].txt[len] = 0;
	list_size++;
	if (list_size % 1000 == 0) {
		printf("loaded %d\r", list_size);
		fflush(stdout);
	}
}

#define BUF_SIZE	(128 * 1024)

int main(int argc, char **argv)
{
	FILE *fin, *fout;
	char *buf;
	int ret, i, count;
	struct block_list *list2;
	struct stat st;

	if (argc < 3) {
		printf("Usage: ./program <input> <output>\n");
		perror("open: ");
		exit(1);
	}

	fin = fopen(argv[1], "r");
	fout = fopen(argv[2], "w");
	if (!fin || !fout) {
		printf("Usage: ./program <input> <output>\n");
		perror("open: ");
		exit(1);
	}

	check_regcomp(&ts_nsec_pattern, "ts\\s*([0-9]*)\\s*ns");

	fstat(fileno(fin), &st);
	max_size = st.st_size / 100; /* hack ... */

	list = malloc(max_size * sizeof(*list));
	buf = malloc(BUF_SIZE);
	if (!list || !buf) {
		printf("Out of memory\n");
		exit(1);
	}

	for ( ; ; ) {
		ret = read_block(buf, BUF_SIZE, fin);
		if (ret < 0)
			break;

		add_list(buf, ret);
	}

	printf("loaded %d\n", list_size);

	printf("sorting ....\n");

	qsort(list, list_size, sizeof(list[0]), compare_txt);

	list2 = malloc(sizeof(*list) * list_size);

	printf("culling\n");

	for (i = count = 0; i < list_size; i++) {
		if (count == 0 ||
		    strcmp(list2[count-1].txt, list[i].txt) != 0) {
			list2[count++] = list[i];
		} else {
			list2[count-1].num += list[i].num;
		}
	}

	qsort(list2, count, sizeof(list[0]), compare_num);

	for (i = 0; i < count; i++)
		fprintf(fout, "%d times:\n%s\n", list2[i].num, list2[i].txt);

	regfree(&ts_nsec_pattern);
	return 0;
}
