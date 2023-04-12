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

Rebasing
--------

When a new major version of Linux is released upstream, we can rebase the
os-build branch.

Rebasing from time to time, helps reduce the clutter of the extra changes
on top of upstream and future merge conflicts. This periodic rebase addresses
the needs of the Fedora community's desire to separate upstream from Fedora
specific changes, helps keep it clear what patches changed in the final form
upstream, and what a Fedora specific patch looks like currently as opposed to
split across various conflict patches.

While rebasing has a negative effect on developer contribution, we believe
saving the rebase for the end of release cycle allows for minimal developer
contribution disruption while gaining the above advantages.

This process is open to feedback for improvements.

To do the os-build rebase, the following steps can be done:

::

   # Create a rebase branch from latest os-build branch and start the process
   # For any conflicts that arise, check and fix them, following git instructions
   git fetch origin
   git checkout -b rebase origin/os-build
   marker=$(cat redhat/marker)
   git rebase $marker

   # After you finish the rebase, check the results against the current os-build
   git diff origin/os-build..
   # If there are differences shown, you might have fixed conflicts wrongly or
   # in a different way. To fix, you may want to add extra on top commits and
   # rebase again interactively
   <make change related to a previous commit to make it equal os-build> && git add
   # create dummy commit
   git commit
   # You may need to create more than one commit, if changes are related to
   # more than one previous commit. Then squash commits into the existing
   # previous commits related to the change with:
   git rebase -i $marker

   # Now cleanup any commits that we might have reverted, and release commits.
   # When editor opens with the commit list in interactive mode, search for any
   # commits starting with "Revert " in the subject and if they match a previous
   # commit which is being reverted, you can remove both. For release commits,
   # search commits with subject starting with "[redhat] kernel-" and delete/
   # remove them
   git rebase -i $marker

   # Check results again doing a diff against os-build branch. Because of cleanup
   # in the previous step, some differences will appear now, and that's ok
   # because of the removal of the release commits. The only differences that
   # should appear are on Makefile.rhelver, redhat/kernel.changelog and
   # redhat/marker
   git diff origin/os-build..

   # If differences shown are expected, we are ok and rebase is done.
   # Check if origin didn't change by fetching again. If origin/os-build
   # changed, you might need to do a rebase again or cherry-pick latest ark
   # only changes into the rebase branch
   git fetch origin
   <if origin/os-build changed, fix up, fetch origin again ... loop>

   # We can now force push/update the os-build branch. Also save the current
   # os-build branch just for backup purposes
   git checkout -b os-build-save origin/os-build
   git checkout os-build
   git reset --hard rebase
   git push -f origin os-build os-build-save

::

   TODO FILL ME IN

