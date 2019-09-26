This directory is part of the DRM backport for RHEL, and contains compatibility
shims for various kernel headers so that upstream DRM code needs minimal
modifications in order to compile against the rest of the kernel infrastructure
for RHEL. These shims are generally wrappers around various portions of the
kernel API that have changed upstream but not downstream.

			How to add compatibility headers

Let's say we want to add a compatibility shim for linux/mm.h, that does
something simple like:

	...
	#define totalram_pages() totalram_pages
	...

We would simply add a header file in include/rm-backport/linux/mm.h that looks
like this:

	#ifndef _RH_DRM_BACKPORT_LINUX_MM_H
	#define _RH_DRM_BACKPORT_LINUX_MM_H

	/* Note the use of #include_next instead of #include, this forces
	 * GCC to look for <linux/mm.h> in header directories which come -AFTER-
	 * the directory which this header was found in.
	 */
	#include_next <linux/mm.h>

	/* So we keep things unchanged for users outside of the DRM
	 * backport */
	#ifdef RH_DRM_BACKPORT

	/* Finally, the actual shim code */
	#define totalram_pages() totalram_pages

	#endif
	#endif

And we're done :)
