// SPDX-License-Identifier: GPL-2.0
/* Copyright (c) 2020 Facebook */
#include "bpf_iter.h"
#include "bpf_tracing_net.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

char _license[] SEC("license") = "GPL";

extern bool CONFIG_IPV6_SUBTREES __kconfig __weak;

SEC("iter/ipv6_route")
int dump_ipv6_route(struct bpf_iter__ipv6_route *ctx)
{
	struct seq_file *seq = ctx->meta->seq;
	struct fib6_info *rt = ctx->rt;
	const struct net_device *dev;
	struct fib6_nh *fib6_nh;
	unsigned int flags;

	if (rt == (void *)0)
		return 0;

	fib6_nh = &rt->fib6_nh;
	flags = rt->fib6_flags;

	BPF_SEQ_PRINTF(seq, "%pi6 %02x ", &rt->fib6_dst.addr, rt->fib6_dst.plen);

	if (CONFIG_IPV6_SUBTREES)
		BPF_SEQ_PRINTF(seq, "%pi6 %02x ", &rt->fib6_src.addr,
			       rt->fib6_src.plen);
	else
		BPF_SEQ_PRINTF(seq, "00000000000000000000000000000000 00 ");

	if (flags & RTF_GATEWAY) {
		BPF_SEQ_PRINTF(seq, "%pi6 ", &fib6_nh->nh_gw);
	} else {
		BPF_SEQ_PRINTF(seq, "00000000000000000000000000000000 ");
	}

	dev = fib6_nh->nh_dev;
	if (dev)
		BPF_SEQ_PRINTF(seq, "%08x %08x %08x %08x %8s\n", rt->fib6_metric,
			       rt->fib6_ref.counter, 0, flags, dev->name);
	else
		BPF_SEQ_PRINTF(seq, "%08x %08x %08x %08x\n", rt->fib6_metric,
			       rt->fib6_ref.counter, 0, flags);

	return 0;
}
