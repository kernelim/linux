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
* Leave the checkboxes blank (or select them if desired).
* Click 'Mirror Repository'. The first update will take about 20 minutes.


Building packages
-----------------

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

With the ``os-build`` branch checked out, build a source RPM package:

.. code-block:: sh

   make dist-srpm

You can now build the binary RPM packages however you would like:

.. code-block:: sh

   # Build packages locally in Mock
   mock redhat/rpm/SRPMS/kernel-*.src.rpm
   # Build packages in Fedora's Koji
   koji build --scratch rawhide redhat/rpm/SRPMS/kernel-*.src.rpm
   koji build --scratch eln redhat/rpm/SRPMS/kernel-*.src.rpm

Want to add a patch? Just apply it with ``git cherry-pick`` or ``git am``, and
re-run ``make dist-srpm``. To modify the kernel configuration, make changes in
``redhat/configs/`` (consult the repository layout for details on this).


Contributor Guide
=================

.. toctree::
   :maxdepth: 2

   repository-layout
   submitting-contributions


Maintainer Guide
================

.. toctree::
   :maxdepth: 2

   maintaining


.. _GitLab account: https://gitlab.com/users/sign_in#register-pane
.. _personal GitLab projects: https://gitlab.com/?name=kernel-ark&personal=true
.. _Fork the repository: https://gitlab.com/cki-project/kernel-ark/-/forks/new
.. _register your SSH key: https://gitlab.com/-/profile/keys
.. _Koji: https://fedoraproject.org/wiki/Using_the_Koji_build_system#Koji_Setup
.. _Mock: https://fedoraproject.org/wiki/Using_Mock_to_test_package_builds#How_do_I_set_up_Mock.3F


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
