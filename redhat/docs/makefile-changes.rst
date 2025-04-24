.. _makefile-changes:

===================
Makefile Guidelines
===================

The Red Hat Makefiles in the /redhat directory are

.. code-block:: sh

   Makefile
   Makefile.cross
   Makefile.rhpkg
   Makefile.variables

Each of these Makefiles serves a specific purpose.

Makefile
========

This file's purpose is to create an SRPM.  Other targets in this Makefile
create kernel config files, submit SRPMS to build systems (brew and koji),
and other SRPM construction operations.

Variables declared in this Makefile are not stable (see Makefile.variables
section) and may change without notice.  The variables are exported for use by
scripts called in the targets.

Makefile.cross
==============

This file's purpose is to supply easy-to-use cross compiling targets.  The
Makefile was written with the assumption that the host architecture is x86_64.

Makefile.rhpkg
==============

This file contains variables that can be overidden by declarations in
~/.rhpkg.mk or $(TOPDIR)/.rhpkg.mk.

Makefile.variables
==================

This file's purpose is to provide a list of stable variables for use by
external scripts.  Variables in this file should be considered stable.
Variables still may be deprecated and will follow the guidelines in
"Deprecating variables and targets" section below.

Variable Naming
===============

Variables names prefixed with SPEC indicate that the variable is used
in redhat/kernel.spec.template (see redhat/genspec.sh).

Deprecating variables and targets
=================================

Occasionally developers may make a change that removes a variable from
Makefile.variables or Makefile.rhpkg, or a target from Makefile or
Makefile.cross.

In these cases, the removal will be preceded by a warning on use of the
variable or target execution that is output to the user.  After two upstream
releases, the variable or target will be removed from the Makefiles.

For example

.. code-block:: sh

  ifdef BREW_FLAGS
    # deprecated in 5.17.0
    $(warning WARNING: BREW_FLAGS will be deprecated in a later release, use BUILD_FLAGS instead.)
  endif

or,

.. code-block:: sh

  dist-kernelversion:
    # deprecated in 5.17.0
    @echo "WARNING: This target will be removed in a later release."
    @echo $(SPECVERSION)-$(DISTRO_BUILD)
