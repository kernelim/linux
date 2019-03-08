/*
 * Copyright IBM Corp. 2008,2009
 *
 *   Author(s): Heiko Carstens <heiko.carstens@de.ibm.com>,
 *
 */

#include <asm/asm-offsets.h>
#include <asm/nospec-insn.h>

	GEN_BR_THUNK %r14

	.globl ftrace_stub
ftrace_stub:
	BR_EX	%r14

	.globl _mcount
_mcount:
#ifdef CONFIG_DYNAMIC_FTRACE
	BR_EX	%r14

	.data
	.globl	ftrace_dyn_func
ftrace_dyn_func:
	.quad	ftrace_stub
	.previous

	.globl ftrace_caller
ftrace_caller:
#endif
	larl	%r1,function_trace_stop
	icm	%r1,0xf,0(%r1)
	jnz	ftrace_exit
	stmg	%r2,%r5,32(%r15)
	stg	%r14,112(%r15)
	lgr	%r1,%r15
	aghi	%r15,-160
	stg	%r1,__SF_BACKCHAIN(%r15)
	lgr	%r2,%r14
	lg	%r3,168(%r15)
#ifdef CONFIG_DYNAMIC_FTRACE
	larl	%r14,ftrace_dyn_func
#else
	larl	%r14,ftrace_trace_function
#endif
	lg	%r1,0(%r14)
	BASR_EX	%r14,%r1
#ifdef CONFIG_FUNCTION_GRAPH_TRACER
#ifdef CONFIG_DYNAMIC_FTRACE
	.globl	ftrace_graph_caller
ftrace_graph_caller:
	# This unconditional branch gets runtime patched. Change only if
	# you know what you are doing. See ftrace_enable_graph_caller().
	j	0f
#endif
	lg	%r2,272(%r15)
	lg	%r3,168(%r15)
	brasl	%r14,prepare_ftrace_return
	stg	%r2,168(%r15)
0:
#endif
	aghi	%r15,160
	lmg	%r2,%r5,32(%r15)
	lg	%r14,112(%r15)
ftrace_exit:
	BR_EX	%r14

#ifdef CONFIG_FUNCTION_GRAPH_TRACER

	.globl	return_to_handler
return_to_handler:
	stmg	%r2,%r5,32(%r15)
	lgr	%r1,%r15
	aghi	%r15,-160
	stg	%r1,__SF_BACKCHAIN(%r15)
	brasl	%r14,ftrace_return_to_handler
	aghi	%r15,160
	lgr	%r14,%r2
	lmg	%r2,%r5,32(%r15)
	BR_EX	%r14

#endif
