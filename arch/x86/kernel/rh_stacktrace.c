/*
 * This file contains stacktrace functions that are in RHEL kABI whitelist.
 */
static int save_stack_address(struct stack_trace *trace, unsigned long addr,
			      bool nosched)
{
	if (nosched && in_sched_functions(addr))
		return 0;

	if (trace->skip > 0) {
		trace->skip--;
		return 0;
	}

	if (trace->nr_entries >= trace->max_entries)
		return -1;

	trace->entries[trace->nr_entries++] = addr;
	return 0;
}

static void noinline __save_stack_trace(struct stack_trace *trace,
			       struct task_struct *task, struct pt_regs *regs,
			       bool nosched)
{
	struct unwind_state state;
	unsigned long addr;

	if (regs)
		save_stack_address(trace, regs->ip, nosched);

	for (unwind_start(&state, task, regs, NULL); !unwind_done(&state);
	     unwind_next_frame(&state)) {
		addr = unwind_get_return_address(&state);
		if (!addr || save_stack_address(trace, addr, nosched))
			break;
	}

	if (trace->nr_entries < trace->max_entries)
		trace->entries[trace->nr_entries++] = ULONG_MAX;
}

/*
 * Save stack-backtrace addresses into a stack_trace buffer.
 */
void save_stack_trace(struct stack_trace *trace)
{
	trace->skip++;
	__save_stack_trace(trace, current, NULL, false);
}
EXPORT_SYMBOL_GPL(save_stack_trace);

void save_stack_trace_tsk(struct task_struct *tsk, struct stack_trace *trace)
{
	if (!try_get_task_stack(tsk))
		return;

	if (tsk == current)
		trace->skip++;
	__save_stack_trace(trace, tsk, NULL, true);

	put_task_stack(tsk);
}
EXPORT_SYMBOL_GPL(save_stack_trace_tsk);
