.. _repository-layout:

=================
Repository Layout
=================

The repository is based on the upstream Linux kernel tree. All branches
except master, though, are downstream-only.

Branches
--------

os-build, a.k.a "the development branch"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The os-build branch is the development branch of the tree.  The os-build branch
tracks the latest version of the kernel patches for ARK and Fedora, as well as
the kernel configuration and build scripts.  This is the branch to send
merge request to.  When a new release is made, this branch is merged into the
release branch.  Configuration and build scripts can be found in the
``redhat/`` directory. Refer to the Configuration section below for more
details.

master
~~~~~~

The master branch tracks `Linus's master
branch <git://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git>`__
(i.e. "mainline").

ark-latest
~~~~~~~~~~

This branch points to the latest release branch.  This branch may differ
slightly from os-build and contain critical patches that resolve compile or
boot issues.  **This is not a development branch, do not base merge requests
off this branch.**

Release branches
~~~~~~~~~~~~~~~~

Each time the kernel is rebased, a set of branches is created to track
that release.

.. _arkpatchesvxy-rcn:

ark/patches/vX.Y[-rcN]
^^^^^^^^^^^^^^^^^^^^^^

Branches in this format (e.g. ``ark/patches/v5.4-rc1`` or
``ark/patches/v5.3``) contain the kernel patches ARK carries for that
particular kernel release. These are merged into the ``ark/vX.Y``
release branches.

.. _arkvxy-rcn:

ark/vX.Y[-rcN]
^^^^^^^^^^^^^^

Branches in this format (e.g. ``ark/v5.4-rc1`` or ``ark/v5.3``) contain
the set of patches that were added on top of the upstream kernel release
along with the configuration and build scripts. They can be checked out
and built into RPMs. The ``master`` branch points to the latest version
of these branches.

Tags
----

.. _vxy-rcn:

vX.Y[-rcN]
~~~~~~~~~~

Tags in this format (e.g. ``v5.4-rc1`` or ``v5.3``) are the upstream
Linux kernel tags from Linus's tree.

.. _kernel-xyz-ndist-and-kernel-xyz-0rcnyyyymmddgitshort-hashdist:

kernel-X.Y.Z-N.<dist> and kernel-X.Y.Z-0.rcN.YYYYMMDDgit<short-hash>.<dist>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tags in this format (e.g. ``kernel-5.4.0-1.elrdy``,
``kernel-5.6.0-1.fc33``, or
``kernel-5.6.0-0.rc5.20200314gitabcd1234.fc33``) map to the RPM
name-version-release tuple in the build system. These can be used to
check out the source tree used to build that RPM. Tags with the
``elrdy`` dist are Always Ready kernel releases and tags with the
``fcNN`` dist are Fedora kernels.

The tags come in two varieties. The first is kernel builds based off an
upstream tag. ``kernel-5.4.0-1.elrdy`` and ``kernel-5.6.0-0.rc6.fc33``
fall into this category. The second variety, which includes a date and
commit hash, is based off a snapshot of Linus's master branch for that
particular day. The git commit hash included in the release is the
commit in Linus's tree the build is based on, *not* the commit in the
Fedora source tree.

Fedora RPM tagging in the ARK kernel began in May 2020 for fc33.  Previous
RPM tags are not available in the ARK kernel tree.

Configuration
-------------

The configuration layout is somewhat complicated. All configuration is
located on the ``os-build`` branch in ``redhat/configs/``. Inside this
directory there are a number of scripts used to automatically generate
complete configurations, along with a number of directories that contain
configuration snippets. At this time, there are three main configuration
directories: ``ark``, ``common``, and ``fedora``. ``ark`` and ``fedora``
are configuration "flavors", while ``common`` is shared configuration
across flavors.

A flavor is defined by:

1. Adding the flavor name to ``redhat/configs/flavors`` on its own line.
2. Create a directory using your flavor name in ``redhat/configs/`` that
   matches the layout of other flavors.
3. Defining a configuration priority by creating a file called
   ``redhat/configs/priority.$flavorname``. This file needs to define a
   number of bash variables that describe the priority of the various
   configuration directories and should include the directory you
   defined in step 2.

common and common-pending
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``common`` directory contains configuration values that are shared
across all configuration "flavors". For a configuration to be in
``common``, it MUST be reviewed and approved by one or more Red Hat
subsystem maintainers since it affects ARK. A flavor's configurations
can override settings in ``common``, so it's not guaranteed settings in
common are the same across all flavors. It's simply a good place to set
common values across the flavors and use as a base for new flavors.

``common-pending`` is where configuration options that have not been
reviewed are placed. Automation creates snippets for all new
configuration options exposed during a rebase of ARK in the
``pending-common`` directory, at which point subsystem maintainers
review the options and set them as appropriate before moving them into
``common``.

New ARK configurations are placed in ``common-pending`` because it is
assumed that ARK generally has the most conservative settings, whereas
other flavors like Fedora will be (for the most part) a superset of the
ARK configuration.

fedora and fedora-pending
~~~~~~~~~~~~~~~~~~~~~~~~~

The ``fedora`` directory contains settings that have been reviewed by
Fedora kernel maintainers for the Fedora Rawhide kernel.

Since Fedora tends to turn on more things than ARK, it's common for a
rebase to expose new configuration options that only apply to Fedora.
For this reason, Fedora has a ``pending-fedora`` directory as well.
``pending-fedora`` contains settings that are not exposed by the
``common`` configuration set and only apply to Fedora. It is, like
``pending-common``, populated automatically during a rebase. A Fedora
kernel maintain can review the settings at their leisure and move them
over to ``fedora`` as they do so.
