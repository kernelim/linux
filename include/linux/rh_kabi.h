/*
 * rh_kabi.h - Red Hat kABI abstraction header
 *
 * Copyright (c) 2014 Don Zickus
 * Copyright (c) 2015-2020 Jiri Benc
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
 * NOTE
 *   Unless indicated otherwise, don't use ';' after these macros as it
 *   messes up the kABI checker by changing what the resulting token string
 *   looks like.  Instead let the macros add the ';' so it can be properly
 *   hidden from the kABI checker (mainly for RH_KABI_EXTEND, but applied to
 *   most macros for uniformity).
 *
 *
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
 * RH_KABI_EXTEND_WITH_SIZE
 *   Adds a new element (usually a struct) to a struct and reserves extra
 *   space for the new element.  The provided 'size' is the total space to
 *   be added in longs (i.e. it's 8 * 'size' bytes), including the size of
 *   the added element.  It is automatically checked that the new element
 *   does not overflow the reserved space, now nor in the future. However,
 *   no attempt is done to check the content of the added element (struct)
 *   for kABI conformance - kABI checking inside the added element is
 *   effectively switched off.
 *   For any struct being added by RH_KABI_EXTEND_WITH_SIZE, it is
 *   recommended its content to be documented as not covered by kABI
 *   guarantee.
 *
 * RH_KABI_FILL_HOLE
 *   Simple macro for filling a hole in a struct.
 *
 *   Warning: only use if a hole exists for _all_ arches.  Use pahole to verify.
 *
 * RH_KABI_RENAME
 *   Simple macro for renaming an element without changing its type.  This
 *   macro can be used in bitfields, for example.
 *
 *   NOTE: this macro does not add the final ';'
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
 * RH_KABI_HIDE_INCLUDE
 *   Hides the given include file from kABI checksum computations.  This is
 *   used when a newly added #include makes a previously opaque struct
 *   visible.
 *
 *   Example usage:
 *   #include RH_KABI_HIDE_INCLUDE(<linux/poll.h>)
 *
 * RH_KABI_FAKE_INCLUDE
 *   Pretends inclusion of the given file for kABI checksum computations.
 *   This is used when upstream removed a particular #include but that made
 *   some structures opaque that were previously visible and is causing kABI
 *   checker failures.
 *
 *   Example usage:
 *   #include RH_KABI_FAKE_INCLUDE(<linux/rhashtable.h>)
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
 * RH_KABI_BROKEN_INSERT
 * RH_KABI_BROKEN_REMOVE
 *   Insert a field to the middle of a struct / delete a field from a struct.
 *   Note that this breaks kABI! It can be done only when it's certain that
 *   no 3rd party driver can validly reach into the struct.  A typical
 *   example is a struct that is:  both (a) referenced only through a long
 *   chain of pointers from another struct that is part of a whitelisted
 *   symbol and (b) kernel internal only, it should have never been visible
 *   to genksyms in the first place.
 *
 *   Another example are structs that are explicitly exempt from kABI
 *   guarantee but we did not have enough foresight to use RH_KABI_EXCLUDE.
 *   In this case, the warning for RH_KABI_EXCLUDE applies.
 *
 *   A detailed explanation of correctness of every RH_KABI_BROKEN_* macro
 *   use is especially important.
 *
 * RH_KABI_BROKEN_INSERT_BLOCK
 * RH_KABI_BROKEN_REMOVE_BLOCK
 *   A version of RH_KABI_BROKEN_INSERT / REMOVE that allows multiple fields
 *   to be inserted or removed together.  All fields need to be terminated
 *   by ';' inside(!) the macro parameter.  The macro itself must not be
 *   terminated by ';'.
 *
 */

#undef linux
#define linux linux

#ifdef __GENKSYMS__

# define RH_KABI_CONST
# define RH_KABI_EXTEND(_new)
# define RH_KABI_FILL_HOLE(_new)
# define RH_KABI_FORCE_CHANGE(ver)		__attribute__((rh_kabi_change ## ver))
# define RH_KABI_RENAME(_orig, _new)		_orig
# define RH_KABI_HIDE_INCLUDE(_file)		<linux/rh_kabi.h>
# define RH_KABI_FAKE_INCLUDE(_file)		_file
# define RH_KABI_BROKEN_INSERT(_new)
# define RH_KABI_BROKEN_REMOVE(_orig)		_orig;
# define RH_KABI_BROKEN_INSERT_BLOCK(_new)
# define RH_KABI_BROKEN_REMOVE_BLOCK(_orig)	_orig

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
# define RH_KABI_HIDE_INCLUDE(_file)		_file
# define RH_KABI_FAKE_INCLUDE(_file)		<linux/rh_kabi.h>
# define RH_KABI_BROKEN_INSERT(_new)		_new;
# define RH_KABI_BROKEN_REMOVE(_orig)
# define RH_KABI_BROKEN_INSERT_BLOCK(_new)	_new
# define RH_KABI_BROKEN_REMOVE_BLOCK(_orig)


#if IS_BUILTIN(CONFIG_RH_KABI_SIZE_ALIGN_CHECKS)
# define __RH_KABI_CHECK_SIZE_ALIGN(_orig, _new)			\
	union {								\
		_Static_assert(sizeof(struct{_new;}) <= sizeof(struct{_orig;}), \
			       __FILE__ ":" __stringify(__LINE__) ": "  __stringify(_new) " is larger than " __stringify(_orig) RH_KABI_ALIGN_WARNING); \
		_Static_assert(__alignof__(struct{_new;}) <= __alignof__(struct{_orig;}), \
			       __FILE__ ":" __stringify(__LINE__) ": "  __stringify(_orig) " is not aligned the same as " __stringify(_new) RH_KABI_ALIGN_WARNING); \
	}
# define __RH_KABI_CHECK_SIZE(_item, _size)				\
	_Static_assert(sizeof(struct{_item;}) <= _size,			\
		       __FILE__ ":" __stringify(__LINE__) ": " __stringify(_item) " is larger than the reserved size (" __stringify(_size) " bytes)" RH_KABI_ALIGN_WARNING)
#else
# define __RH_KABI_CHECK_SIZE_ALIGN(_orig, _new)
# define __RH_KABI_CHECK_SIZE(_item, _size)
#endif

#define RH_KABI_UNIQUE_ID	__PASTE(rh_kabi_hidden_, __LINE__)

# define _RH_KABI_DEPRECATE(_type, _orig)	_type rh_reserved_##_orig
# define _RH_KABI_DEPRECATE_FN(_type, _orig, _args...)  \
	_type (* rh_reserved_##_orig)(_args)
# define _RH_KABI_REPLACE(_orig, _new)			  \
	union {						  \
		_new;					  \
		struct {				  \
			_orig;				  \
		} RH_KABI_UNIQUE_ID;			  \
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
 * Extending a struct while reserving extra space.
 */
#define RH_KABI_EXTEND_WITH_SIZE(_new, _size)				\
	RH_KABI_EXTEND(union {						\
		_new;							\
		unsigned long RH_KABI_UNIQUE_ID[_size];			\
		__RH_KABI_CHECK_SIZE(_new, 8 * (_size));		\
	})

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
