// SPDX-License-Identifier: GPL-2.0
// Copyright(c) 2018 Linus Torvalds. All rights reserved.
// Copyright(c) 2018 Alexei Starovoitov. All rights reserved.
// Copyright(c) 2018 Intel Corporation. All rights reserved.

#ifndef _LINUX_NOSPEC_H
#define _LINUX_NOSPEC_H

struct task_struct;

/* Speculation control prctl */
int arch_prctl_spec_ctrl_get(struct task_struct *task, unsigned long which);
int arch_prctl_spec_ctrl_set(struct task_struct *task, unsigned long which,
			     unsigned long ctrl);
/* Speculation control for seccomp enforced mitigation */
void arch_seccomp_spec_mitigate(struct task_struct *task);

#endif /* _LINUX_NOSPEC_H */
