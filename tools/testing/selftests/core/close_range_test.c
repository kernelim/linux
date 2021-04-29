// SPDX-License-Identifier: GPL-2.0

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/kernel.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syscall.h>
#include <unistd.h>
#include <sched.h>
#include <signal.h>

#include "../kselftest_harness.h"

#ifndef __NR_close_range
#define __NR_close_range -1
#endif

#ifndef CLOSE_RANGE_UNSHARE
#define CLOSE_RANGE_UNSHARE	(1U << 1)
#endif

static inline int sys_close_range(unsigned int fd, unsigned int max_fd,
				  unsigned int flags)
{
	return syscall(__NR_close_range, fd, max_fd, flags);
}

#ifndef ARRAY_SIZE
#define ARRAY_SIZE(x) (sizeof(x) / sizeof((x)[0]))
#endif

TEST(close_range)
{
	int i, ret;
	int open_fds[101];

	for (i = 0; i < ARRAY_SIZE(open_fds); i++) {
		int fd;

		fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
		ASSERT_GE(fd, 0) {
			if (errno == ENOENT)
				SKIP(return, "Skipping test since /dev/null does not exist");
		}

		open_fds[i] = fd;
	}

	EXPECT_EQ(-1, sys_close_range(open_fds[0], open_fds[100], -1)) {
		if (errno == ENOSYS)
			SKIP(return, "close_range() syscall not supported");
	}

	EXPECT_EQ(0, sys_close_range(open_fds[0], open_fds[50], 0));

	for (i = 0; i <= 50; i++)
		EXPECT_EQ(-1, fcntl(open_fds[i], F_GETFL));

	for (i = 51; i <= 100; i++)
		EXPECT_GT(fcntl(open_fds[i], F_GETFL), -1);

	/* create a couple of gaps */
	close(57);
	close(78);
	close(81);
	close(82);
	close(84);
	close(90);

	EXPECT_EQ(0, sys_close_range(open_fds[51], open_fds[92], 0));

	for (i = 51; i <= 92; i++)
		EXPECT_EQ(-1, fcntl(open_fds[i], F_GETFL));

	for (i = 93; i <= 100; i++)
		EXPECT_GT(fcntl(open_fds[i], F_GETFL), -1);

	/* test that the kernel caps and still closes all fds */
	EXPECT_EQ(0, sys_close_range(open_fds[93], open_fds[99], 0));

	for (i = 93; i <= 99; i++)
		EXPECT_EQ(-1, fcntl(open_fds[i], F_GETFL));

	EXPECT_GT(fcntl(open_fds[i], F_GETFL), -1);

	EXPECT_EQ(0, sys_close_range(open_fds[100], open_fds[100], 0));

	EXPECT_EQ(-1, fcntl(open_fds[100], F_GETFL));
}

struct arg {
	int open_fds[101];
};

int fn(void *p)
{
	int i, ret;
	struct arg *arg = (struct arg *)(p);
	int *open_fds = arg->open_fds;

	ret = sys_close_range(open_fds[0], open_fds[50],
			      CLOSE_RANGE_UNSHARE);
	if (ret)
		exit(EXIT_FAILURE);

	for (i = 0; i <= 50; i++)
		if (fcntl(open_fds[i], F_GETFL) != -1)
			exit(EXIT_FAILURE);

	for (i = 51; i <= 100; i++)
		if (fcntl(open_fds[i], F_GETFL) == -1)
			exit(EXIT_FAILURE);

	/* create a couple of gaps */
	close(57);
	close(78);
	close(81);
	close(82);
	close(84);
	close(90);

	ret = sys_close_range(open_fds[51], open_fds[92],
			      CLOSE_RANGE_UNSHARE);
	if (ret)
		exit(EXIT_FAILURE);

	for (i = 51; i <= 92; i++)
		if (fcntl(open_fds[i], F_GETFL) != -1)
			exit(EXIT_FAILURE);

	for (i = 93; i <= 100; i++)
		if (fcntl(open_fds[i], F_GETFL) == -1)
			exit(EXIT_FAILURE);

	/* test that the kernel caps and still closes all fds */
	ret = sys_close_range(open_fds[93], open_fds[99],
			CLOSE_RANGE_UNSHARE);
	if (ret)
		exit(EXIT_FAILURE);

	for (i = 93; i <= 99; i++)
		if (fcntl(open_fds[i], F_GETFL) != -1)
			exit(EXIT_FAILURE);

	if (fcntl(open_fds[100], F_GETFL) == -1)
		exit(EXIT_FAILURE);

	ret = sys_close_range(open_fds[100], open_fds[100],
			      CLOSE_RANGE_UNSHARE);
	if (ret)
		exit(EXIT_FAILURE);

	if (fcntl(open_fds[100], F_GETFL) != -1)
		exit(EXIT_FAILURE);

	exit(EXIT_SUCCESS);
}


TEST(close_range_unshare)
{
	int i, status;
	pid_t pid;
	struct arg arg;
	const unsigned int stack_size = 1024 * 1024;
	void *stack;

	for (i = 0; i < ARRAY_SIZE(arg.open_fds); i++) {
		int fd;

		fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
		ASSERT_GE(fd, 0) {
			if (errno == ENOENT)
				SKIP(return, "Skipping test since /dev/null does not exist");
		}

		arg.open_fds[i] = fd;
	}

	stack = malloc(stack_size);
	if (stack == NULL)
		exit(EXIT_FAILURE);

	pid = clone(fn, stack + stack_size - 1, CLONE_FILES | SIGCHLD, (void *)&arg);
	ASSERT_GE(pid, 0);

	EXPECT_EQ(waitpid(pid, &status, 0), pid);
	EXPECT_EQ(true, WIFEXITED(status));
	EXPECT_EQ(0, WEXITSTATUS(status));
	free(stack);
}

int fn_capped(void *p)
{
	int i, ret;
	struct arg *arg = (struct arg *)(p);
	int *open_fds = arg->open_fds;

	ret = sys_close_range(open_fds[0], UINT_MAX,
			CLOSE_RANGE_UNSHARE);
	if (ret)
		exit(EXIT_FAILURE);

	for (i = 0; i <= 100; i++)
		if (fcntl(open_fds[i], F_GETFL) != -1)
			exit(EXIT_FAILURE);

	exit(EXIT_SUCCESS);
}

TEST(close_range_unshare_capped)
{
	int i, ret, status;
	pid_t pid;
	struct arg arg;
	const unsigned int stack_size = 1024 * 1024;
	void *stack;

	for (i = 0; i < ARRAY_SIZE(arg.open_fds); i++) {
		int fd;

		fd = open("/dev/null", O_RDONLY | O_CLOEXEC);
		ASSERT_GE(fd, 0) {
			if (errno == ENOENT)
				SKIP(return, "Skipping test since /dev/null does not exist");
		}

		arg.open_fds[i] = fd;
	}

	stack = malloc(stack_size);
	if (stack == NULL)
		exit(EXIT_FAILURE);

	pid = clone(fn_capped, stack + stack_size - 1, CLONE_FILES | SIGCHLD, (void *)&arg);
	ASSERT_GE(pid, 0);

	EXPECT_EQ(waitpid(pid, &status, 0), pid);
	EXPECT_EQ(true, WIFEXITED(status));
	EXPECT_EQ(0, WEXITSTATUS(status));
	free(stack);
}

TEST_HARNESS_MAIN
