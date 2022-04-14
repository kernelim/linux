===========
Maintenance
===========

This guide covers common maintenance tasks and is primarily aimed at
kernel maintainers. It assumes you have write access to
`https://gitlab.com/cki-project/kernel-ark.git <https://gitlab.com/cki-project/kernel-ark.git>`__
and the remote in your clone is called "upstream", as set up in the
quick start guide.

The repository is used for both the Fedora kernel and the RHEL Always
Ready kernel (ARK). Thus, it contains two sets of configurations.

Every release requires the maintainer to:

1. Update the configuration
2. Create a release branch and/or tag

Once that is done, the result can be imported into a dist-git repository
and built in Koji.

There is a script to automate the entire process which is run nightly by
CI/CD. You can run it locally:

::

   # Ensure we've got a clean check out for all the branches we're about to use
   git checkout master && git pull
   git checkout os-build && git pull

   # Create a release based on "master", which tracks mainline
   make dist-fedora-release

The individual steps taken are described below for the curious.

Configuration
-------------

Update the configuration branch:

Merges in the latest upstream 'master' changes and sets defaults for any new
configuration files:

::

   make dist-merge-upstream

Or to auto-push changes

::

   make dist-merge-upstream-push

Common Problems
~~~~~~~~~~~~~~~

There are a few issues that can occur during the configuration update
due to merge conflicts.

Merge Conflicts
^^^^^^^^^^^^^^^

When merging the master branch, existing Red Hat patches may conflict with
changes pushed upstream.  Use best judgement to resolve them.  If the fix
requires more than a trivial context change, reach out reach out to RHEL
developers for guidance based on the RHMAINTIANERS file.

Release branch
--------------

Once the kernel patches and configuration have been updated for the new
release, it's time to create the release branch and/or tag. If this is a
snapshot build (i.e. master does not point to a tag), we only create a
tag.

To build against a specific release use TAG=<git tag> otherwise the scripts
default to 'master'.

::

   make dist-fedora-release
   (use TAG=<git tag> for a specific tag)

Or to auto-push changes

::

   make dist-fedora-release-push
   (use TAG=<git tag> for a specific tag)

Building
--------

After a release branch has been prepared, it's time to build it. This
guide assumes you have Koji and/or Brew installed and properly
configured. It also assumes you've authenticated and have permissions to
build.

Fedora
~~~~~~

This requires having fedpkg installed.

From the release branch/tag, run:

::

   # Checks out the Fedora dist-git repository and copies everything from the source tree into it
   #
   # By default, this creates a directory in /tmp, but the location can be set with RHDISTGIT_TMP.
   # If you already have a local clone of the Fedora dist-git repository, it can be used with RHDISTGIT_CACHE=<path-to-repo>.
   #
   # localversion sets the buildid, releases should have an empty build id
   rm localversion
   touch localversion
   make dist-dist-git

   cd /tmp/RHEL*/kernel
   git commit -a -s -F ../changelog
   fedpkg push
   fedpkg build

ELN
~~~

This build is automatically kicked off upon successfull completion of the
above Fedora build.

To kick off manually run

::

   TODO FILL ME IN

