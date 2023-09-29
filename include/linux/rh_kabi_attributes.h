#ifndef _LINUX_RH_KABI_ATTRIBTUES_H
#define _LINUX_RH_KABI_ATTRIBTUES_H

/*
 * Renaming selective compiler attributes to the original form to avoid
 * breaking kABI.
 */
#ifdef __GENKSYMS__

#define __designated_init__		designated_init
#define __externally_visible__		externally_visible
#define __format__			format
#define __no_instrument_function__	no_instrument_function
#define __packed__			packed
#define __warn_unused_result__		warn_unused_result

#endif
#endif /* _LINUX_RH_KABI_ATTRIBTUES_H */
