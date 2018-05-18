// SPDX-License-Identifier: GPL-2.0
// Copyright(c) 2018 Linus Torvalds. All rights reserved.
// Copyright(c) 2018 Alexei Starovoitov. All rights reserved.
// Copyright(c) 2018 Intel Corporation. All rights reserved.

#ifndef _LINUX_NOSPEC_H
#define _LINUX_NOSPEC_H

/* Speculation control prctl */
int arch_prctl_spec_ctrl_get(unsigned long which);
int arch_prctl_spec_ctrl_set(unsigned long which, unsigned long ctrl);

#endif /* _LINUX_NOSPEC_H */
