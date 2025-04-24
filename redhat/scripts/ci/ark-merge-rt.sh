#!/bin/bash
#
# This script is intended to sync up the RT and automotive branch (derivative
# of RT).  It adds the extra twist of detecting the right upstream rt branch
# to sync with depending on the existance of the next branch.  Sometimes the
# rt-devel branch waits until -rc1/2 to create new branches.
# Finally the code handles the rebases in those cases where newer branches
# are available.
#
# Why the complexity?
# Development branches will need to be periodically rebased unfortunately.
# Using 'git rebase --onto <new head> <old_head>' only works with one common
# branch to rebase from not two.  Meanwhile, the -devel branches are formed
# from two upstream branches, os-build and linux-rt-devel.  The idea is
# to merge the two branches into a single throwaway branch that can be
# recreated from scratch anytime then use that as the base for -devel.

set -e

# source common CI functions and variables
# shellcheck disable=SC1091
. "$(dirname "$0")"/ark-ci-env.sh

#Upstream RT tree git://git.kernel.org/pub/scm/linux/kernel/git/rt/linux-rt-devel.git
UPSTREAM_RT_TREE_URL="git://git.kernel.org/pub/scm/linux/kernel/git/rt/linux-rt-devel.git"
UPSTREAM_RT_TREE_NAME="linux-rt-devel"
RT_DEVEL_BRANCH="os-build-rt-devel"
AUTOMOTIVE_DEVEL_BRANCH="os-build-automotive-devel"

# verify git remote rt is setup
if ! git remote get-url "$UPSTREAM_RT_TREE_NAME" 2>/dev/null; then
	die "Please 'git remote add linux-rt-devel $UPSTREAM_RT_TREE_URL'"
fi

# grab the os-build base branches
ark_git_mirror "os-build" "origin" "os-build"
ark_git_mirror "master" "origin" "master"

# make sure tags are available for git-describe to correctly work
git fetch -t origin

# what are the current versions of rt-devel and os-build (use 'master' to
# avoid fedora tagging of kernel-X.Y.0.0.....)
# use git tags which are always 'vX.Y-rcZ-aaa-gbbbbb' or 'vX.Y-aaa-gbbbbb'
# where X.Y is the version number that maps to linux-rt's branch of
# 'linux-X.Y.y'
get_upstream_version()
{
	branch=$1
	upstream="master"

	# Thanks to pre-rc1 merging, we have a 2 week window with an
	# incorrect version number.  Detect and correct.
	mergebase="$(git merge-base "$branch" "$upstream")"
	raw_version="$(git describe "$mergebase")"
	version="$(git show "$branch":Makefile | sed -ne '/^VERSION\ =\ /{s///;p;q}')"
	patchlevel="$(git show "$branch":Makefile | sed -ne '/^PATCHLEVEL\ =\ /{s///;p;q}')"
	rhelrel="$(git show "$branch":Makefile.rhelver | sed -ne '/^RHEL_RELEASE\ =\ /{s///;p;q}')"
	kver="${version}.${patchlevel}"

	#-rc indicates no tricks necessary, return version
	if echo "${raw_version}" | grep -q -- "-rc"; then
		echo "$kver"
		return
	fi

	#must be a post tag release with -g but not -rcX, IOW an rc0.
	if echo "${raw_version}" | grep -q -- "-g"; then
		#Add a 1 to the version number
		echo "${version}.$((patchlevel + 1))"
		return
	fi

	#if -gXXX is _not_ there, must be a GA release, but there are 2 GA releases:
	#pre-rebase and post-rebase.

	#post-rebase resets the RHEL_RELEASE
	#treat like the beginning of rc0 and bump version
	#7 is arbituary and ties to a minimum of 7 RCs
	if ((rhelrel < 7)); then
		#Add a 1 to the version number
		echo "${version}.$((patchlevel + 1))"
		return
	fi

	#pre-rebase
	echo "$kver"
}

# To handle missing branches, precalculate previous kernel versions to fetch
get_prev_version()
{
	version_str=$1

	version="$(echo "$version_str" | cut -d'.' -f1)"
	patchlevel="$(echo "$version_str" | cut -d'.' -f2)"

	echo "${version}.$((patchlevel - 1))"
}

OS_BUILD_VER="$(get_upstream_version os-build)"
OS_BUILD_VER_prev="$(get_prev_version "$OS_BUILD_VER")"

# upstream -rt devel branches are aligned with version numbers and are not
# always up to date with master.  Figure out which branch to mirror based on
# version number and existance.  We may have to trigger a rebase.

# check latest upstream RT branch
OS_BUILD_PREV_BASE_BRANCH="origin/archived-${OS_BUILD_VER_prev}"
if git fetch -q "$UPSTREAM_RT_TREE_NAME" "linux-${OS_BUILD_VER}.y-rt"; then
	UPSTREAM_RT_DEVEL_VER="${OS_BUILD_VER}"
	OS_BUILD_BASE_BRANCH="os-build"
elif git fetch -q "$UPSTREAM_RT_TREE_NAME" "linux-${OS_BUILD_VER_prev}.y-rt"; then
	UPSTREAM_RT_DEVEL_VER="${OS_BUILD_VER_prev}"
	OS_BUILD_BASE_BRANCH="$OS_BUILD_PREV_BASE_BRANCH"
else
	die "Neither version ($OS_BUILD_VER, $OS_BUILD_VER_prev) in upstream tree: $UPSTREAM_RT_TREE_NAME"
fi

UPSTREAM_RT_PREV_BRANCH=""

# verify the core branches exist or use provided defaults
UPSTREAM_RT_DEVEL_BRANCH="linux-${UPSTREAM_RT_DEVEL_VER}.y-rt"
ark_git_branch "$RT_DEVEL_BRANCH" "$OS_BUILD_BASE_BRANCH"
ark_git_branch "$AUTOMOTIVE_DEVEL_BRANCH" "$OS_BUILD_BASE_BRANCH"

RT_DEVEL_VER="$(get_upstream_version $RT_DEVEL_BRANCH)"
AUTOMOTIVE_DEVEL_VER="$(get_upstream_version $AUTOMOTIVE_DEVEL_BRANCH)"

# handle rebasing
if test "$UPSTREAM_RT_DEVEL_VER" != "$RT_DEVEL_VER" -o \
	"$UPSTREAM_RT_DEVEL_VER" != "$AUTOMOTIVE_DEVEL_VER"; then

	# we need the previous rt branch for rebase purposes
	UPSTREAM_RT_PREV_BRANCH="linux-${OS_BUILD_VER_prev}.y-rt"
	git fetch -q "$UPSTREAM_RT_TREE_NAME" "$UPSTREAM_RT_PREV_BRANCH"

	# handle the rebase
	# rebases usually go from prev version to new version
	# rebuild the prev merge base as it isn't saved.
	# then rebuild the current merge base as it isn't saved either
	prev_branch="$(git rev-parse --abbrev-ref HEAD)"
	temp_prev_branch="_temp_prev_rt_devel_$(date +%F)"
	git branch -D "$temp_prev_branch" 2>/dev/null || true
	git fetch "$UPSTREAM_RT_TREE_NAME" "$UPSTREAM_RT_PREV_BRANCH"
	git checkout -b "$temp_prev_branch" "$OS_BUILD_PREV_BASE_BRANCH"
	msg="Merge branch $UPSTREAM_RT_TREE_NAME/$UPSTREAM_RT_PREV_BRANCH"
	git merge -m "$msg" "$UPSTREAM_RT_TREE_NAME/$UPSTREAM_RT_PREV_BRANCH"

	# create devel merge branch to base merge on.
	temp_devel_branch="_temp_devel_rt_devel_$(date +%F)"
	git branch -D "$temp_devel_branch" 2>/dev/null || true
	git checkout -b "$temp_devel_branch" "$OS_BUILD_BASE_BRANCH"
	msg="Merge branch $UPSTREAM_RT_TREE_NAME/$UPSTREAM_RT_DEVEL_BRANCH"
	git merge -m "$msg" "$UPSTREAM_RT_TREE_NAME/$UPSTREAM_RT_DEVEL_BRANCH"

	git checkout "$prev_branch"
        # do the git rebase --onto $temp_devel_branch $temp_prev_branch
	prev_rt_branch="$(git rev-parse $RT_DEVEL_BRANCH)"

	# rt-devel branch AUTOMATIC config merges will conflict with
	# os-build AUTOMATIC merges if -stable makes changes.  Filter them
	# out and let them properly come in through os-build.
	# The conflicts are in the text sections of pending-fedora/rhel
	# configs.
	export GIT_SEQUENCE_EDITOR="sed -i '/AUTOMATIC/d;/Remove rt pending/d'"
	ark_git_rebase "$RT_DEVEL_BRANCH" "$temp_prev_branch" "$temp_devel_branch"

	# use the pre-rebase rt-devel branch and the post-rebase rt-devel
	# branch as input to git rebase
	ark_git_rebase "$AUTOMOTIVE_DEVEL_BRANCH" "$prev_rt_branch" "$RT_DEVEL_BRANCH"
	git branch -D "$temp_prev_branch"
	git branch -D "$temp_devel_branch"
	export -n "GIT_SEQUENCE_EDITOR"

	# allow force git push
	export ARK_REBASE="true"
fi

## Build -rt-devel branch, generate pending-rhel configs
ark_git_merge "$RT_DEVEL_BRANCH" "$OS_BUILD_BASE_BRANCH"
ark_git_merge "$RT_DEVEL_BRANCH" "$UPSTREAM_RT_TREE_NAME/$UPSTREAM_RT_DEVEL_BRANCH"
# don't care if configs were added or not hence '|| true'
ark_update_configs "$RT_DEVEL_BRANCH" || true
# skip pushing config update MRs, keep them in pending-rhel
ark_push_changes "$RT_DEVEL_BRANCH" "skip"

## Build -automotive-devel branch based on the rt-devel branch, generate
## pending-rhel configs
ark_git_merge "$AUTOMOTIVE_DEVEL_BRANCH" "$RT_DEVEL_BRANCH"
# don't care if configs were added or not hence '|| true'
ark_update_configs "$AUTOMOTIVE_DEVEL_BRANCH" || true
# skip pushing config update MRs, keep them in pending-rhel
ark_push_changes "$AUTOMOTIVE_DEVEL_BRANCH" "skip"
