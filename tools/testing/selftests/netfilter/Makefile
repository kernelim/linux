# SPDX-License-Identifier: GPL-2.0
# Makefile for netfilter selftests

TEST_PROGS := nft_trans_stress.sh nft_nat.sh \
	conntrack_icmp_related.sh nft_flowtable.sh ipvs.sh \
	nft_queue.sh nft_meta.sh \
	conntrack_tcp_unreplied.sh

LDLIBS = -lmnl
TEST_GEN_FILES =  nf-queue

include ../lib.mk
