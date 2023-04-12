.. Fedora Kernel and ARK Documentation documentation master file, created by
   sphinx-quickstart on Thu May  7 14:44:56 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=================
Fedora/ARK Kernel
=================

This documentation covers setting up a development environment, the repository
layout, and the general contribution workflow.

.. _quick-start:

Quick Start
===========

Setup
-----

To start with you need to:

1. Make a `GitLab account`_ if you do not already have one.
2. `Fork the repository`_. Wait patiently for this to complete.
3. Configure pull mirroring on your fork (see below).
4. Set up `Koji`_ or `Mock`_ if desired.

Pull mirroring keeps your fork in sync and avoids the need to configure a
separate remote in Git. Once GitLab finishes forking the repository:

* Go to your fork from your `personal GitLab projects`_.
* In the sidebar, click 'Settings' and then 'Repository'.
* Next to 'Mirroring repositories', click 'Expand'.
* Enter the Git repository URL: https://gitlab.com/cki-project/kernel-ark.git
* Ensure the 'Mirror direction' is 'Pull'.
* Leave the 'Password' blank.
* Select 'Overwrite diverged branches' (ARK rebases every GA release)
* Leave the other checkboxes blank (or select them if desired).
* Click 'Mirror Repository'. The first update will take about 20 minutes.

Cloning the Repository
----------------------

Install the dependencies for generating source RPM packages:

.. code-block:: sh

   sudo dnf install git make gcc flex bison bzip2 rpm-build

Then clone the repository. To use SSH, `register your SSH key`_ in GitLab first.

.. code-block:: sh

   # Clone using SSH
   git clone git@gitlab.com:${GITLAB_USER_NAME}/kernel-ark.git && cd kernel-ark
   # Clone using HTTPS
   git clone https://gitlab.com/${GITLAB_USER_NAME}/kernel-ark.git && cd kernel-ark

The ``os-build`` branch is checked out automatically after cloning. This
branch contains the configuration and build scripts, and it is regularly
updated to work with Linus's master branch.

The ``ark-latest`` branch contains a very recent 'known-good' version of the
os-build branch that can be used if the os-build branch does not compile due to
upstream bugs.  However, the os-build branch must be used as a Merge Request
target for all Fedora/ARK specific changes.

Build Dependencies
------------------

kernel-ark has a long list of BuildRequires that are specified in the
kernel.spec file.  Built-in rpm commands like 'yum builddep' will not
work on all OSes (`see BZ 2103214`_),
and 'yum deplist' which requires the configuration and enabling of a source
repository.  As a result a 'dist-get-buildreqs' target has been added that will
provide a list of missing dependencies.  This list can be consumed by other
commands to install missing packages:

.. code-block:: sh

   # install missing build dependencies
   yum -y install $(make dist-get-buildreqs | grep "Missing dependencies:" | cut -d":" -f2)

Some packages may require the enabling of additional repositories such as the
system-sb-certs package which can be found in a Centos-Stream or RHEL CodeReady
Linux Builder (CRB) repository.

Local builds
------------

With the ``os-build`` or ``ark-latest`` branch checked out, get the kernel .config:

.. code-block:: sh

   make dist-configs # or make dist-configs-arch
   cp redhat/configs/<flavor_os>.config .config

You can now execute any common upstream make targets (make, make -j, make cscope, etc.).

Building packages
-----------------

With the ``os-build`` or ``ark-latest`` branch checked out, build a source RPM package:

.. code-block:: sh

   make dist-srpm

You can now build the binary RPM packages however you would like:

.. code-block:: sh

   # Build packages locally in Mock
   mock redhat/rpm/SRPMS/kernel-*.src.rpm
   # Build packages in Fedora's Koji
   koji build --scratch rawhide redhat/rpm/SRPMS/kernel-*.src.rpm
   koji build --scratch eln redhat/rpm/SRPMS/kernel-*.src.rpm

or

.. code-block:: sh

   # this target requires internal Red Hat network access and will always
   # build against the latest RHEL major compose
   make dist-brew

The dist-brew target can be used with the BUILD_FLAGS variable to specify specific architectures.  For example, to only build the x86_64 and noarch architectures,

.. code-block:: sh

   # this target requires internal Red Hat network access and will always
   # build against the latest RHEL major compose
   make dist-brew BUILD_FLAGS="--arch-override=x86_64,noarch"

Want to add a patch? Just apply it with ``git cherry-pick`` or ``git am``, and
re-run ``make dist-srpm``. To modify the kernel configuration, make changes in
``redhat/configs/`` (consult the repository layout for details on this).


Contributor Guide
=================

.. toctree::
   :maxdepth: 2

   repository-layout
   submitting-contributions
   faq
   makefile-changes
   kernel-naming


Maintainer Guide
================

.. toctree::
   :maxdepth: 2

   maintaining


.. _GitLab account: https://gitlab.com/users/sign_in#register-pane
.. _personal GitLab projects: https://gitlab.com/?name=kernel-ark&personal=true
.. _Fork the repository: https://gitlab.com/cki-project/kernel-ark/-/forks/new
.. _register your SSH key: https://gitlab.com/-/profile/keys
.. _Koji: https://docs.fedoraproject.org/en-US/package-maintainers/Using_the_Koji_Build_System/
.. _Mock: https://fedoraproject.org/wiki/Using_Mock_to_test_package_builds#How_do_I_set_up_Mock.3F
.. _see BZ 2103214: https://bugzilla.redhat.com/2103214


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
