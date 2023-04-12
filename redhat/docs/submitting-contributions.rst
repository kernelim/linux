========================
Submitting Contributions
========================

Thanks for considering contributing to the Fedora and Always Ready
kernels, we really appreciate it! Before you get started, please
familiarize yourself with the general `Fedora kernel
policies <https://docs.fedoraproject.org/en-US/quick-docs/kernel/overview/#_policies>`__.

These guides assume you've completed the :ref:`quick-start` guide
and are familiar with the :ref:`repository-layout`.

All contributions must be constructed against the ``os-build`` branch
which contains the configs for Fedora and ARK builds, and the kernel patches
for Fedora and ARK.

Documentation
=============

Contributions to the documentation are always welcome. This documentation is
written with `Sphinx <https://www.sphinx-doc.org/>`_. Your distribution should
provide a Sphinx package, or you can set up an environment and build the
documentation as HTML with::

    python3 -m venv ~/.virtualenvs/ark-docs
    source ~/.virtualenvs/ark-docs/bin/activate
    pip install Sphinx
    cd redhat/docs
    make html

Your documentation changes should build in Sphinx without warnings and this is
enforced by CI. You can check your changes locally with::

    make SPHINXOPTS="-W" html

Patches
=======

Quick start:

1. ``git fetch orgin``
2. ``git checkout -b my-build-change origin/os-build``
3. Make a change to a file.
4. Add your changes with ``git add -A``.
5. Commit your changes and write a nice commit message that explains the
   change: ``git commit -s``.
6. Open a merge request. You can do so via the web UI, or directly from
   a git push with
   ``git push -o merge_request.create -u <your-remote> my-build-change``
   (defaults to target branch ``os-build``). Refer to the `push
   options <https://docs.gitlab.com/ee/user/project/push_options.html>`__
   documentation for more details.

Configuration Changes
---------------------

Each configuration option for the kernel is placed in its own file
inside the ``redhat/configs/<flavor>/`` directory.

Each file must be named after the configuration option it contains.

To disable a particular setting, the file must contain
``# CONFIG_TOWEL is not set`` rather than ``CONFIG_TOWEL=n`` where
CONFIG_TOWEL is replaced with the actual configuration option.

The directory is hierarchical by architecture families. The top level is
generic configurations that apply across most architectures. Within
that, there are directories like ``arm``, ``powerpc``, and ``x86`` where
architecture specific configurations are placed. Settings in these
architecture-specific directories override any duplicate settings in the
more generic directories. Configurations that are specific to a
particular architecture should be placed in that architecture's
directory rather in the generic directory.

Configuration changes in the ``common`` and ``ark`` directories require
review from Red Hat kernel developers, where-as the configurations in
``fedora`` can be changed with the approval of the Fedora kernel
maintainers.

Makefile changes
----------------

Guidelines for makefile target and variable changes are found in the :ref:`makefile-changes` doc.

Commit messages
---------------

Each commit you make should contain a detailed description of *why* the
change is necessary. For example, if the commit enables or disables a
configuration option, explain exactly why the change is necessary. If
there is a Bugzilla bug relating to the change, please include a
reference to it using the format ``Bugzilla: <url>``. For example:

::

   Enable CONFIG_TOWEL so kernels never panic

   Since the beginning the kernel has panicked. This has made a lot of people very
   angry and has widely been regarded as a bad move. This new configuration option
   solves all the kernel's problems and now it never panics.

   Bugzilla: https://bugzilla.redhat.com/show_bug.cgi?id=1234567890
   Signed-off-by: Jeremy Cline <jcline@redhat.com>

Kernel code patches should be submitted upstream prior to being sent for
inclusion in Fedora. The commit message for the patch should be the same
as upstream, except for the addition of a few tags the message.

Upstream Status
~~~~~~~~~~~~~~~

Each commit should contain an ``Upstream Status`` tag to indicate where
the patch can be found. Some examples:

A patch that's been sent upstream, but is not yet in a sub-maintainer's
tree should link to the email:

::

   Upstream Status: https://lore.kernel.org/lkml/20200220151738.1492852-1-jcline@redhat.com/

A patch that's been accepted into an upstream maintainer's tree should
reference the tree and should also include the upstream commit in the
format used by ``git cherry-pick -x``:

::

   Upstream Status: netdev/net-next.git
   (cherry picked from commit aed145ccb4918b8b6f7855be9dc6067bd48e4124)

If the tree isn't hosted on kernel.org, ``Upstream Status`` should link
to it.

Finally, a downstream-only patch should be marked:

::

   Upstream Status: RHEL only

Bugzilla
~~~~~~~~

As with configuration and build script changes, if there is a Bugzilla
bug relating to the kernel commit, please include a reference to it
using the format ``Bugzilla: <url>``.

Continuous Integration
======================

Tests are run on each merge request to ensure it does not introduce
regressions. The test definitions are located at
`https://gitlab.com/cki-project/kernel-ark-ci <https://gitlab.com/cki-project/kernel-ark-ci>`__.
Since both main development branches need similar tests, the branches
within this repository reference the CI definition there so they only
need to be maintained in a single place.

Licensing
=========

Your commit messages must include a Signed-off-by tag with your name and
e-mail address, indicating that you agree to the `Developer Certificate
of Origin <https://developercertificate.org/>`__ version 1.1:

::

   Developer Certificate of Origin
   Version 1.1

   Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
   1 Letterman Drive
   Suite D4700
   San Francisco, CA, 94129

   Everyone is permitted to copy and distribute verbatim copies of this
   license document, but changing it is not allowed.


   Developer's Certificate of Origin 1.1

   By making a contribution to this project, I certify that:

   (a) The contribution was created in whole or in part by me and I
       have the right to submit it under the open source license
       indicated in the file; or

   (b) The contribution is based upon previous work that, to the best
       of my knowledge, is covered under an appropriate open source
       license and I have the right under that license to submit that
       work with modifications, whether created in whole or in part
       by me, under the same open source license (unless I am
       permitted to submit under a different license), as indicated
       in the file; or

   (c) The contribution was provided directly to me by some other
       person who certified (a), (b) or (c) and I have not modified
       it.

   (d) I understand and agree that this project and the contribution
       are public and that a record of the contribution (including all
       personal information I submit with it, including my sign-off) is
       maintained indefinitely and may be redistributed consistent with
       this project or the open source license(s) involved.

Use ``git commit -s`` to add the Signed-off-by tag.
