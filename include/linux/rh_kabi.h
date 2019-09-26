/*
 * rh_kabi.h - Red Hat kABI abstraction header
 *
 * Copyright (c) 2014 Don Zickus
 * Copyright (c) 2015-2018 Jiri Benc
 * Copyright (c) 2015 Sabrina Dubroca, Hannes Frederic Sowa
 * Copyright (c) 2016-2018 Prarit Bhargava
 * Copyright (c) 2017 Paolo Abeni, Larry Woodman
 *
 * This file is released under the GPLv2.
 * See the file COPYING for more details.
 *
 * These kabi macros hide the changes from the kabi checker and from the
 * process that computes the exported symbols' checksums.
 * They have 2 variants: one (defined under __GENKSYMS__) used when
 * generating the checksums, and the other used when building the kernel's
 * binaries.
 *
 * The use of these macros does not guarantee that the usage and modification
 * of code is correct.  As with all Red Hat only changes, an engineer must
 * explain why the use of the macro is valid in the patch containing the
 * changes.
 *
 */

#ifndef _LINUX_RH_KABI_H
#define _LINUX_RH_KABI_H

#include <linux/compiler.h>
#include <linux/stringify.h>

/*
 * RH_KABI_CONST
 *   Adds a new const modifier to a function parameter preserving the old
 *   checksum.
 *
 * RH_KABI_DEPRECATE
 *   Mark the element as deprecated and make it unusable by modules while
 *   preserving kABI checksums.
 *
 * RH_KABI_DEPRECATE_FN
 *   Mark the function pointer as deprecated and make it unusable by modules
 *   while preserving kABI checksums.
 *
 * RH_KABI_EXTEND
 *   Simple macro for adding a new element to a struct.
 *
 *   Warning: only use if a hole exists for _all_ arches.  Use pahole to verify.
 *
 * RH_KABI_FILL_HOLE
 *   Simple macro for filling a hole in a struct.
 *
 * RH_KABI_RENAME
 *   Simple macro for renaming an element without changing its type.  This
 *   macro can be used in bitfields, for example.
 *
 *   NOTE: does not include the final ';'
 *
 * RH_KABI_REPLACE
 *   Simple replacement of _orig with a union of _orig and _new.
 *
 *   The RH_KABI_REPLACE* macros attempt to add the ability to use the '_new'
 *   element while preserving size alignment with the '_orig' element.
 *
 *   The #ifdef __GENKSYMS__ preserves the kABI agreement, while the anonymous
 *   union structure preserves the size alignment (assuming the '_new' element
 *   is not bigger than the '_orig' element).
 *
 * RH_KABI_REPLACE_UNSAFE
 *   Unsafe version of RH_KABI_REPLACE.  Only use for typedefs.
 *
 * RH_KABI_FORCE_CHANGE
 *   Force change of the symbol checksum.  The argument of the macro is a
 *   version for cases we need to do this more than once.
 *
 *   This macro does the opposite: it changes the symbol checksum without
 *   actually changing anything about the exported symbol.  It is useful for
 *   symbols that are not whitelisted, we're changing them in an
 *   incompatible way and want to prevent 3rd party modules to silently
 *   corrupt memory.  Instead, by changing the symbol checksum, such modules
 *   won't be loaded by the kernel.  This macro should only be used as a
 *   last resort when all other KABI workarounds have failed.
 *
 * RH_KABI_EXCLUDE
 *   !!! WARNING: DANGEROUS, DO NOT USE unless you are aware of all the !!!
 *   !!! implications. This should be used ONLY EXCEPTIONALLY and only  !!!
 *   !!! under specific circumstances. Very likely, this macro does not !!!
 *   !!! do what you expect it to do. Note that any usage of this macro !!!
 *   !!! MUST be paired with a RH_KABI_FORCE_CHANGE annotation of       !!!
 *   !!! a suitable symbol (or an equivalent safeguard) and the commit  !!!
 *   !!! log MUST explain why the chosen solution is appropriate.       !!!
 *
 *   Exclude the element from checksum generation.  Any such element is
 *   considered not to be part of the kABI whitelist and may be changed at
 *   will.  Note however that it's the responsibility of the developer
 *   changing the element to ensure 3rd party drivers using this element
 *   won't panic, for example by not allowing them to be loaded.  That can
 *   be achieved by changing another, non-whitelisted symbol they use,
 *   either by nature of the change or by using RH_KABI_FORCE_CHANGE.
 *
 *   Also note that any change to the element must preserve its size. Change
 *   of the size is not allowed and would constitute a silent kABI breakage.
 *   Beware that the RH_KABI_EXCLUDE macro does not do any size checks.
 *
 * NOTE
 *   Don't use ';' after these macros as it messes up the kABI checker by
 *   changing what the resulting token string looks like.  Instead let this
 *   macro add the ';' so it can be properly hidden from the kABI checker
 *   (mainly for RH_KABI_EXTEND, but applied to all macros for uniformity).
 *
 */
#ifdef __GENKSYMS__

# define RH_KABI_CONST
# define RH_KABI_EXTEND(_new)
# define RH_KABI_FILL_HOLE(_new)
# define RH_KABI_FORCE_CHANGE(ver)		__attribute__((rh_kabi_change ## ver))
# define RH_KABI_RENAME(_orig, _new)		_orig

# define _RH_KABI_DEPRECATE(_type, _orig)	_type _orig
# define _RH_KABI_DEPRECATE_FN(_type, _orig, _args...)	_type (*_orig)(_args)
# define _RH_KABI_REPLACE(_orig, _new)		_orig
# define _RH_KABI_REPLACE_UNSAFE(_orig, _new)	_orig
# define _RH_KABI_EXCLUDE(_elem)

#else

# define RH_KABI_ALIGN_WARNING ".  Disable CONFIG_RH_KABI_SIZE_ALIGN_CHECKS if debugging."

# define RH_KABI_CONST				const
# define RH_KABI_EXTEND(_new)			_new;
# define RH_KABI_FILL_HOLE(_new)		_new;
# define RH_KABI_FORCE_CHANGE(ver)
# define RH_KABI_RENAME(_orig, _new)		_new


#if IS_BUILTIN(CONFIG_RH_KABI_SIZE_ALIGN_CHECKS)
# define __RH_KABI_CHECK_SIZE_ALIGN(_orig, _new)			\
	union {								\
		_Static_assert(sizeof(struct{_new;}) <= sizeof(struct{_orig;}), \
			       __FILE__ ":" __stringify(__LINE__) ": "  __stringify(_new) " is larger than " __stringify(_orig) RH_KABI_ALIGN_WARNING); \
		_Static_assert(__alignof__(struct{_new;}) <= __alignof__(struct{_orig;}), \
			       __FILE__ ":" __stringify(__LINE__) ": "  __stringify(_orig) " is not aligned the same as " __stringify(_new) RH_KABI_ALIGN_WARNING); \
	}
#else
# define __RH_KABI_CHECK_SIZE_ALIGN(_orig, _new)
#endif

# define _RH_KABI_DEPRECATE(_type, _orig)	_type rh_reserved_##_orig
# define _RH_KABI_DEPRECATE_FN(_type, _orig, _args...)  \
	_type (* rh_reserved_##_orig)(_args)
# define _RH_KABI_REPLACE(_orig, _new)			  \
	union {						  \
		_new;					  \
		struct {				  \
			_orig;				  \
		} __UNIQUE_ID(rh_kabi_hide);		  \
		__RH_KABI_CHECK_SIZE_ALIGN(_orig, _new);  \
	}
# define _RH_KABI_REPLACE_UNSAFE(_orig, _new)	_new

# define _RH_KABI_EXCLUDE(_elem)		_elem

#endif /* __GENKSYMS__ */

/* semicolon added wrappers for the RH_KABI_REPLACE macros */
# define RH_KABI_DEPRECATE(_type, _orig)	_RH_KABI_DEPRECATE(_type, _orig);
# define RH_KABI_DEPRECATE_FN(_type, _orig, _args...)  \
	_RH_KABI_DEPRECATE_FN(_type, _orig, _args);
# define RH_KABI_REPLACE(_orig, _new)		_RH_KABI_REPLACE(_orig, _new);
# define RH_KABI_REPLACE_UNSAFE(_orig, _new)	_RH_KABI_REPLACE_UNSAFE(_orig, _new);
/*
 * Macro for breaking up a random element into two smaller chunks using an
 * anonymous struct inside an anonymous union.
 */
# define RH_KABI_REPLACE2(orig, _new1, _new2)	RH_KABI_REPLACE(orig, struct{ _new1; _new2;})

# define RH_KABI_RESERVE(n)		_RH_KABI_RESERVE(n);
/*
 * Simple wrappers to replace standard Red Hat reserved elements.
 */
# define RH_KABI_USE(n, _new)		RH_KABI_REPLACE(_RH_KABI_RESERVE(n), _new)
/*
 * Macros for breaking up a reserved element into two smaller chunks using
 * an anonymous struct inside an anonymous union.
 */
# define RH_KABI_USE2(n, _new1, _new2)	RH_KABI_REPLACE(_RH_KABI_RESERVE(n), struct{ _new1; _new2; })

/*
 * We tried to standardize on Red Hat reserved names.  These wrappers
 * leverage those common names making it easier to read and find in the
 * code.
 */
# define _RH_KABI_RESERVE(n)		unsigned long rh_reserved##n

#define RH_KABI_EXCLUDE(_elem)		_RH_KABI_EXCLUDE(_elem);

/*
 * RHEL macros to extend structs.
 *
 * base struct: The struct being extended.  For example, pci_dev.
 * extended struct: The Red Hat struct being added to the base struct.
 *		    For example, pci_dev_rh.
 *
 * These macros should be used to extend structs before KABI freeze.
 * They can be used post-KABI freeze in the limited case of the base
 * struct not being embedded in another struct.
 *
 * Extended structs cannot be shrunk in size as changes will break
 * the size & offset comparison.
 *
 * Extended struct elements are not guaranteed for access by modules unless
 * explicitly commented as such in the declaration of the extended struct or
 * the element in the extended struct.
 */

/*
 * RH_KABI_SIZE_AND_EXTEND|_PTR() extends a struct by embedding or adding
 * a pointer in a base struct.  The name of the new struct is the name
 * of the base struct appended with _rh.
 */
#define _RH_KABI_SIZE_AND_EXTEND_PTR(_struct)				\
	size_t _struct##_size_rh;					\
	RH_KABI_EXCLUDE(struct _struct##_rh *_struct##_rh)
#define RH_KABI_SIZE_AND_EXTEND_PTR(_struct)				\
	_RH_KABI_SIZE_AND_EXTEND_PTR(_struct)

#define _RH_KABI_SIZE_AND_EXTEND(_struct)				\
	size_t _struct##_size_rh;					\
	RH_KABI_EXCLUDE(struct _struct##_rh _struct##_rh)
#define RH_KABI_SIZE_AND_EXTEND(_struct)				\
	_RH_KABI_SIZE_AND_EXTEND(_struct)

/*
 * RH_KABI_SET_SIZE calculates and sets the size of the extended struct and
 * stores it in the size_rh field for structs that are dynamically allocated.
 * This macro MUST be called when expanding a base struct with
 * RH_KABI_SIZE_AND_EXTEND, and it MUST be called from the allocation site
 * regardless of being allocated in the kernel or a module.
 * Note: since this macro is intended to be invoked outside of a struct,
 * a semicolon is necessary at the end of the line where it is invoked.
 */
#define RH_KABI_SET_SIZE(_name, _struct) ({				\
	_name->_struct##_size_rh = sizeof(struct _struct##_rh);		\
})

/*
 * RH_KABI_INIT_SIZE calculates and sets the size of the extended struct and
 * stores it in the size_rh field for structs that are statically allocated.
 * This macro MUST be called when expanding a base struct with
 * RH_KABI_SIZE_AND_EXTEND, and it MUST be called from the declaration site
 * regardless of being allocated in the kernel or a module.
 */
#define RH_KABI_INIT_SIZE(_struct)					\
	._struct##_size_rh = sizeof(struct _struct##_rh),

/*
 * RH_KABI_CHECK_EXT verifies allocated memory exists.  This MUST be called to
 * verify that memory in the _rh struct is valid, and can be called
 * regardless if RH_KABI_SIZE_AND_EXTEND or RH_KABI_SIZE_AND_EXTEND_PTR is
 * used.
 */
#define RH_KABI_CHECK_EXT(_ptr, _struct, _field) ({			\
	size_t __off = offsetof(struct _struct##_rh, _field);		\
	_ptr->_struct##_size_rh > __off ? true : false;			\
})

#endif /* _LINUX_RH_KABI_H */
