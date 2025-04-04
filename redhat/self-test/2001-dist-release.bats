#!/usr/bin/env bats
# Purpose: These are general dist-release tests.  They are run from a git
# worktree created by the first test.

DIST_RELEASE_REGEX="^\[redhat\] kernel-[0-9.]*"

load test-lib.bash

@test "dist-release setup worktree" {
	git worktree add $BATS_TMPDIR/distrelease
	cd $BATS_TMPDIR/distrelease
	# All the tests start off with 'make dist-release', so we can pull
	# that out and put it here in the prologue:
	DIST=.fc33 make dist-release
}

@test "dist-release test 1" {
	# Test whether a second 'make dist-release' operation creates
	# a second commit.  It SHOULD NOT.
	# Capture 2nd line of log in array; ${loga[0]} is SHA1
	cd $BATS_TMPDIR/distrelease
	loga=($(git log --oneline -n 2 | tail -1))
	DIST=.fc33 make dist-release
	# Capture 2nd line of log in array; ${logb[0]} is SHA1
	logb=($(git log --oneline -n 2 | tail -1))
	# If SHA1 in loga is the same as the SHA1 in logb, then no
	# 2nd commit has been created and the test has succeeded:
	run [ ${loga[0]} = ${logb[0]} ]
	check_status
}

_dist-release_test_2() {
    echo $pkgrelease | grep -q -w "$build"
}

@test "dist-release test 2" {
	# Test whether release number in commit message matches
	# release number in Makefile.rhelver.
	# and above in prologue.
	cd $BATS_TMPDIR/distrelease
	title="$(git log --oneline --grep "${DIST_RELEASE_REGEX}" -n 1 --pretty="format:%s")"
	# title = ... [redhat] kernel-5.11.0-0.rc0.20201220git467f8165a2b0.104
	# Just the title message part AFTER "[redhat] ":
	title=${title##*\[redhat\] }
	# Strip off ...kernel-VV.PP.SS-:
	pkgrelease=${title##*kernel-+([5-9]).+([0-9]).+([0-9])-}
	build=$(BUILD= DIST=.fc33 make dist-dump-variables | grep -E "^BUILD=" | cut -d"=" -f2 | xargs)
	echo "pkgrelease=$pkgrelease"
	echo "build=$build"
	run _dist-release_test_2
	check_status
}

_dist-release_test_3() {
	[ "$changelog" = "$gitlog" ]
}

# Note, when running this test on the command line you may have to specifiy the
# RHEL_MAJOR and RHEL_MINOR variables, for example,
#	RHEL_MAJOR=9 RHEL_MINOR=99 bats redhat/self-test/2001-dist-release.bats
@test "dist-release test 3" {
	# Test whether the version in the commit message matches
	# the version in the change log.
	cd $BATS_TMPDIR/distrelease

	# Extract just the version part (the part between [ ]) on the first line of
	# the change log:
	changelog=$(head -1 ./redhat/kernel.changelog-${RHEL_MAJOR}.${RHEL_MINOR} | sed -e 's/.*\[\(.*\)\].*/\1/')

	# Extract the tag in the latest [redhat] kernel commit message
	commit="$(git log --oneline --grep "${DIST_RELEASE_REGEX}" -n 1 --pretty="format:%s")"
	# Extract just the commit message part AFTER "[redhat] ":
	gitlog=${commit##*\[redhat\] }
	# This time, strip off "kernel-" also:
	gitlog=${gitlog/kernel-/}

	echo "The kernel version in the changelog-${RHEL_MAJOR}.${RHEL_MINOR} ("${changelog}") differs from the version in the git log ($gitlog)"

	run _dist-release_test_3
	check_status
}

@test "dist-release cleanup worktree" {
	git worktree remove --force $BATS_TMPDIR/distrelease
	git branch -D distrelease
}
