#ifndef _TIMEKEEPING_INTERNAL_H
#define _TIMEKEEPING_INTERNAL_H
/*
 * timekeeping debug functions
 */
#include <linux/time.h>
#include <linux/clocksource.h>

#ifdef CONFIG_CLOCKSOURCE_VALIDATE_LAST_CYCLE
static inline cycle_t clocksource_delta(cycle_t now, cycle_t last, cycle_t mask)
{
	cycle_t ret = (now - last) & mask;

	return (s64) ret > 0 ? ret : 0;
}
#else
static inline cycle_t clocksource_delta(cycle_t now, cycle_t last, cycle_t mask)
{
	return (now - last) & mask;
}
#endif

#endif /* _TIMEKEEPING_INTERNAL_H */
