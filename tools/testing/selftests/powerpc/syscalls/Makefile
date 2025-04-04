# SPDX-License-Identifier: GPL-2.0-only
TEST_GEN_PROGS := ipc_unmuxed rtas_filter

top_srcdir = ../../../../..
include ../../lib.mk
include ../flags.mk

CFLAGS += -I../../../../../usr/include

$(TEST_GEN_PROGS): ../harness.c
