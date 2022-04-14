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

#include <linux/kconfig.h>
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
 * RH_KABI_ADD_MODIFIER
 *   Adds a new modifier to a function parameter or a typedef, preserving
 *   the old checksum.  Useful e.g. for adding rcu annotations or changing
 *   int to unsigned.  Beware that this may change the semantics; if you're
 *   sure this is safe, always explain why binary compatibility with 3rd
 *   party modules is retained.
 *
 * RH_KABI_DEPRECATE
 *   Marks the element as deprecated and make it unusable by modules while
 *   keeping a hole in its place to preserve binary compatibility.
 *
 * RH_KABI_DEPRECATE_FN
 *   Marks the function pointer as deprecated and make it unusable by modules
 *   while keeping a hole in its place to preserve binary compatibility.
 *
 * RH_KABI_EXTEND
 *   Adds a new field to a struct.  This must always be added to the end of
 *   the struct.  Before using this macro, make sure this is actually safe
 *   to do - there is a number of conditions under which it is *not* safe.
 *   In particular (but not limited to), this macro cannot be used:
 *   - if the struct in question is embedded in another struct, or
 *   - if the struct is allocated by drivers either statically or
 *     dynamically, or
 *   - if the struct is allocated together with driver data (an example of
 *     such behavior is struct net_device or struct request).
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
 *   Fills a hole in a struct.
 *
 *   Warning: only use if a hole exists for _all_ arches.  Use pahole to verify.
 *
 * RH_KABI_RENAME
 *   Renames an element without changing its type.  This macro can be used in
 *   bitfields, for example.
 *
 *   NOTE: this macro does not add the final ';'
 *
 * RH_KABI_REPLACE
 *   Replaces the _orig field by the _new field.  The size of the occupied
 *   space is preserved, it's fine if the _new field is smaller than the
 *   _orig field.  If a _new field is larger or has a different alignment,
 *   compilation will abort.
 *
 * RH_KABI_REPLACE_SPLIT
 *   Works the same as RH_KABI_REPLACE but replaces a single _orig field by
 *   multiple new fields.  The checks for size and alignment done by
 *   RH_KABI_REPLACE are still applied.
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
 * RH_KABI_RESERVE
 *   Adds a reserved field to a struct.  This is done prior to kABI freeze
 *   for structs that cannot be expanded later using RH_KABI_EXTEND (for
 *   example because they are embedded in another struct or because they are
 *   allocated by drivers or because they use unusual memory layout).  The
 *   size of the reserved field is 'unsigned long' and is assumed to be
 *   8 bytes.
 *
 *   The argument is a number unique for the given struct; usually, multiple
 *   RH_KABI_RESERVE macros are added to a struct with numbers starting from
 *   one.
 *
 *   Example usage:
 *   struct foo {
 *           int a;
 *           RH_KABI_RESERVE(1)
 *           RH_KABI_RESERVE(2)
 *           RH_KABI_RESERVE(3)
 *           RH_KABI_RESERVE(4)
 *   };
 *
 * RH_KABI_USE
 *   Uses a previously reserved field or multiple fields.  The arguments are
 *   one or more numbers assigned to RH_KABI_RESERVE, followed by a field to
 *   be put in their place.  The compiler ensures that the new field is not
 *   larger than the reserved area.
 *
 *   Example usage:
 *   struct foo {
 *           int a;
 *           RH_KABI_USE(1, int b)
 *           RH_KABI_USE(2, 3, int c[3])
 *           RH_KABI_RESERVE(4)
 *   };
 *
 * RH_KABI_USE_SPLIT
 *   Works the same as RH_KABI_USE but replaces a single reserved field by
 *   multiple new fields.
 *
 * RH_KABI_AUX_EMBED
 * RH_KABI_AUX_PTR
 *   Adds an extenstion of a struct in the form of "auxiliary structure".
 *   This is done prior to kABI freeze for structs that cannot be expanded
 *   later using RH_KABI_EXTEND.  See also RH_KABI_RESERVED, these two
 *   approaches can (and often are) combined.
 *
 *   To use this for 'struct foo' (the "base structure"), define a new
 *   structure called 'struct foo_rh'; this new struct is called "auxiliary
 *   structure".  Then add RH_KABI_AUX_EMBED or RH_KABI_AUX_PTR to the end
 *   of the base structure.  The argument is the name of the base structure,
 *   without the 'struct' keyword.
 *
 *   RH_KABI_AUX_PTR stores a pointer to the aux structure in the base
 *   struct.  The lifecycle of the aux struct needs to be properly taken
 *   care of.
 *
 *   RH_KABI_AUX_EMBED embeds the aux struct into the base struct.  This
 *   cannot be used when the base struct is itself embedded into another
 *   struct, allocated in an array, etc.
 *
 *   Both approaches (ptr and embed) work correctly even when the aux struct
 *   is allocated by modules.  To ensure this, the code responsible for
 *   allocation/assignment of the aux struct has to properly set the size of
 *   the aux struct; see the RH_KABI_AUX_SET_SIZE and RH_KABI_AUX_INIT_SIZE
 *   macros.
 *
 *   New fields can be later added to the auxiliary structure, always to its
 *   end.  Note the auxiliary structure cannot be shrunk in size later (i.e.,
 *   fields cannot be removed, only deprecated).  Any code accessing fields
 *   from the aux struct must guard the access using the RH_KABI_AUX macro.
 *   The access itself is then done via a '_rh' field in the base struct.
 *
 *   The auxiliary structure is not guaranteed for access by modules unless
 *   explicitly commented as such in the declaration of the aux struct
 *   itself or some of its elements.
 *
 *   Example:
 *
 *   struct foo_rh {
 *           int newly_added;
 *   };
 *
 *   struct foo {
 *           bool big_hammer;
 *           RH_KABI_AUX_PTR(foo)
 *   };
 *
 *   void use(struct foo *f)
 *   {
 *           if (RH_KABI_AUX(f, foo, newly_added))
 *                   f->_rh->newly_added = 123;
 *	     else
 *	             // the field 'newly_added' is not present in the passed
 *	             // struct, fall back to old behavior
 *	             f->big_hammer = true;
 *   }
 *
 *   static struct foo_rh my_foo_rh {
 *           .newly_added = 0;
 *   }
 *
 *   static struct foo my_foo = {
 *           .big_hammer = false,
 *           ._rh = &my_foo_rh,
 *           RH_KABI_AUX_INIT_SIZE(foo)
 *   };
 *
 * RH_KABI_USE_AUX_PTR
 *   Creates an auxiliary structure post kABI freeze.  This works by using
 *   two reserved fields (thus there has to be two reserved fields still
 *   available) and converting them to RH_KABI_AUX_PTR.
 *
 *   Example:
 *
 *   struct foo_rh {
 *   };
 *
 *   struct foo {
 *           int a;
 *           RH_KABI_RESERVE(1)
 *           RH_KABI_USE_AUX_PTR(2, 3, foo)
 *   };
 *
 * RH_KABI_AUX_SET_SIZE
 * RH_KABI_AUX_INIT_SIZE
 *   Calculates and stores the size of the auxiliary structure.
 *
 *   RH_KABI_AUX_SET_SIZE is for dynamically allocated base structs,
 *   RH_KABI_AUX_INIT_SIZE is for statically allocated case structs.
 *
 *   These macros must be called from the allocation (RH_KABI_AUX_SET_SIZE)
 *   or declaration (RH_KABI_AUX_INIT_SIZE) site, regardless of whether
 *   that happens in the kernel or in a module.  Without calling one of
 *   these macros, the aux struct will appear to have no fields to the
 *   kernel.
 *
 *   Note: since RH_KABI_AUX_SET_SIZE is intended to be invoked outside of
 *   a struct definition, it does not add the semicolon and must be
 *   terminated by semicolon by the caller.
 *
 * RH_KABI_AUX
 *   Verifies that the given field exists in the given auxiliary structure.
 *   This MUST be called prior to accessing that field; failing to do that
 *   may lead to invalid memory access.
 *
 *   The first argument is a pointer to the base struct, the second argument
 *   is the name of the base struct (without the 'struct' keyword), the
 *   third argument is the field name.
 *
 *   This macro works for structs extended by either of RH_KABI_AUX_EMBED,
 *   RH_KABI_AUX_PTR and RH_KABI_USE_AUX_PTR.
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
 * RH_KABI_BROKEN_REPLACE
 *   Replace a field by a different one without doing any checking.  This
 *   allows replacing a field by another with a different size.  Similarly
 *   to other RH_KABI_BROKEN macros, use of this indicates a kABI breakage.
 *
 * RH_KABI_BROKEN_INSERT_ENUM
 * RH_KABI_BROKEN_REMOVE_ENUM
 *   Insert a field to the middle of an enumaration type / delete a field from
 *   an enumaration type. Note that this can break kABI especially if the
 *   number of enum fields is used in an array within a structure. It can be
 *   done only when it is certain that no 3rd party driver will use the
 *   enumeration type or a structure that embeds an array with size determined
 *   by an enumeration type.
 *
 * RH_KABI_EXTEND_ENUM
 *   Adds a new field to an enumeration type.  This must always be added to
 *   the end of the enum.  Before using this macro, make sure this is actually
 *   safe to do.
 */

#undef linux
#define linux linux

#ifdef __GENKSYMS__

# define RH_KABI_CONST
# define RH_KABI_ADD_MODIFIER(_new)
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
# define RH_KABI_BROKEN_REPLACE(_orig, _new)	_orig;
# define RH_KABI_BROKEN_INSERT_ENUM(_new)
# define RH_KABI_BROKEN_REMOVE_ENUM(_orig)	_orig,
# define RH_KABI_EXTEND_ENUM(_new)

# define _RH_KABI_DEPRECATE(_type, _orig)	_type _orig
# define _RH_KABI_DEPRECATE_FN(_type, _orig, _args...)	_type (*_orig)(_args)
# define _RH_KABI_REPLACE(_orig, _new)		_orig
# define _RH_KABI_EXCLUDE(_elem)

#else

# define RH_KABI_ALIGN_WARNING ".  Disable CONFIG_RH_KABI_SIZE_ALIGN_CHECKS if debugging."

# define RH_KABI_CONST				const
# define RH_KABI_ADD_MODIFIER(_new)		_new
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
# define RH_KABI_BROKEN_REPLACE(_orig, _new)	_new;
# define RH_KABI_BROKEN_INSERT_ENUM(_new)	_new,
# define RH_KABI_BROKEN_REMOVE_ENUM(_orig)
# define RH_KABI_EXTEND_ENUM(_new)		_new,

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

# define _RH_KABI_EXCLUDE(_elem)		_elem

#endif /* __GENKSYMS__ */

# define RH_KABI_DEPRECATE(_type, _orig)	_RH_KABI_DEPRECATE(_type, _orig);
# define RH_KABI_DEPRECATE_FN(_type, _orig, _args...)  \
	_RH_KABI_DEPRECATE_FN(_type, _orig, _args);
# define RH_KABI_REPLACE(_orig, _new)		_RH_KABI_REPLACE(_orig, _new);

#define _RH_KABI_REPLACE1(_new)		_new;
#define _RH_KABI_REPLACE2(_new, ...)	_new; _RH_KABI_REPLACE1(__VA_ARGS__)
#define _RH_KABI_REPLACE3(_new, ...)	_new; _RH_KABI_REPLACE2(__VA_ARGS__)
#define _RH_KABI_REPLACE4(_new, ...)	_new; _RH_KABI_REPLACE3(__VA_ARGS__)
#define _RH_KABI_REPLACE5(_new, ...)	_new; _RH_KABI_REPLACE4(__VA_ARGS__)
#define _RH_KABI_REPLACE6(_new, ...)	_new; _RH_KABI_REPLACE5(__VA_ARGS__)
#define _RH_KABI_REPLACE7(_new, ...)	_new; _RH_KABI_REPLACE6(__VA_ARGS__)
#define _RH_KABI_REPLACE8(_new, ...)	_new; _RH_KABI_REPLACE7(__VA_ARGS__)
#define _RH_KABI_REPLACE9(_new, ...)	_new; _RH_KABI_REPLACE8(__VA_ARGS__)
#define _RH_KABI_REPLACE10(_new, ...)	_new; _RH_KABI_REPLACE9(__VA_ARGS__)
#define _RH_KABI_REPLACE11(_new, ...)	_new; _RH_KABI_REPLACE10(__VA_ARGS__)
#define _RH_KABI_REPLACE12(_new, ...)	_new; _RH_KABI_REPLACE11(__VA_ARGS__)

#define RH_KABI_REPLACE_SPLIT(_orig, ...)	_RH_KABI_REPLACE(_orig, \
		struct { __PASTE(_RH_KABI_REPLACE, COUNT_ARGS(__VA_ARGS__))(__VA_ARGS__) });

# define RH_KABI_RESERVE(n)		_RH_KABI_RESERVE(n);

#define _RH_KABI_USE1(n, _new)	_RH_KABI_RESERVE(n), _new
#define _RH_KABI_USE2(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE1(__VA_ARGS__)
#define _RH_KABI_USE3(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE2(__VA_ARGS__)
#define _RH_KABI_USE4(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE3(__VA_ARGS__)
#define _RH_KABI_USE5(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE4(__VA_ARGS__)
#define _RH_KABI_USE6(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE5(__VA_ARGS__)
#define _RH_KABI_USE7(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE6(__VA_ARGS__)
#define _RH_KABI_USE8(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE7(__VA_ARGS__)
#define _RH_KABI_USE9(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE8(__VA_ARGS__)
#define _RH_KABI_USE10(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE9(__VA_ARGS__)
#define _RH_KABI_USE11(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE10(__VA_ARGS__)
#define _RH_KABI_USE12(n, ...)	_RH_KABI_RESERVE(n); _RH_KABI_USE11(__VA_ARGS__)

#define _RH_KABI_USE(...)	_RH_KABI_REPLACE(__VA_ARGS__)
#define RH_KABI_USE(n, ...)	_RH_KABI_USE(__PASTE(_RH_KABI_USE, COUNT_ARGS(__VA_ARGS__))(n, __VA_ARGS__));

# define RH_KABI_USE_SPLIT(n, ...)	RH_KABI_REPLACE_SPLIT(_RH_KABI_RESERVE(n), __VA_ARGS__)

# define _RH_KABI_RESERVE(n)		unsigned long rh_reserved##n

#define RH_KABI_EXCLUDE(_elem)		_RH_KABI_EXCLUDE(_elem);

#define RH_KABI_EXTEND_WITH_SIZE(_new, _size)				\
	RH_KABI_EXTEND(union {						\
		_new;							\
		unsigned long RH_KABI_UNIQUE_ID[_size];			\
		__RH_KABI_CHECK_SIZE(_new, 8 * (_size));		\
	})

#define _RH_KABI_AUX_PTR(_struct)					\
	size_t _struct##_size_rh;					\
	_RH_KABI_EXCLUDE(struct _struct##_rh *_rh)
#define RH_KABI_AUX_PTR(_struct)					\
	_RH_KABI_AUX_PTR(_struct);

#define _RH_KABI_AUX_EMBED(_struct)					\
	size_t _struct##_size_rh;					\
	_RH_KABI_EXCLUDE(struct _struct##_rh _rh)
#define RH_KABI_AUX_EMBED(_struct)					\
	_RH_KABI_AUX_EMBED(_struct);

#define RH_KABI_USE_AUX_PTR(n1, n2, _struct)				\
	RH_KABI_USE(n1, n2,						\
		     struct { RH_KABI_AUX_PTR(_struct) })

#define RH_KABI_AUX_SET_SIZE(_name, _struct) ({				\
	(_name)->_struct##_size_rh = sizeof(struct _struct##_rh);	\
})

#define RH_KABI_AUX_INIT_SIZE(_struct)					\
	._struct##_size_rh = sizeof(struct _struct##_rh),

#define RH_KABI_AUX(_ptr, _struct, _field) ({				\
	size_t __off = offsetof(struct _struct##_rh, _field);		\
	(_ptr)->_struct##_size_rh > __off ? true : false;		\
})

#endif /* _LINUX_RH_KABI_H */
