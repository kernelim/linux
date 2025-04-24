#!/bin/bash
#
# Generate a release tag and, if based on a tagged upstream release, a set
# of release branches. This script will rebase the ark-patches branch, update
# os-build with the latest configurations, and apply any merge requests labeled
# with "Include in Releases".

set -e

# This script requires the `gitlab` command to locate `Include in Releases` content.
if ! command -v gitlab > /dev/null 2>&1 ; then
	echo "Required command 'gitlab' (from python-gitlab package) not present."
	exit 1
fi

# source common CI functions and variables
# shellcheck disable=SC1091
. "$(dirname "$0")"/ark-ci-env.sh

git checkout "${BRANCH}"
touch localversion
old_head="$(git rev-parse HEAD)"
make dist-release

# prep ark-latest branch
git checkout --detach "${BRANCH}" && git describe

MR_PATCHES=$(gitlab project-merge-request list --project-id="$PROJECT_ID" \
	--labels="Include in Releases" --state=opened | grep -v "^$" | sort | \
	awk '{ print "https://gitlab.com/cki-project/kernel-ark/-/merge_requests/" $2 ".patch" }')
for patch_url in $MR_PATCHES; do
	curl -sL "$patch_url" | git am -3
done

# if dist-release doesn't update anything, then there is a good chance the
# tag already exists and infra changes have already been applied.  Let's
# skip those conditions and exit gracefully.
make dist-release
new_head="$(git rev-parse HEAD)"
if test "$old_head" == "$new_head"; then
	echo "Nothing changed, skipping updates"
	exit 0
fi

make dist-release-tag
RELEASE=$(git describe) #grab the tag
git checkout ark-latest
git reset --hard "$RELEASE"

# Update ark-infra branch
git checkout ark-infra

# Using ark-latest because it has latest fixes
rm -rf makefile Makefile.rhelver Kconfig.redhat redhat/
git archive --format=tar ark-latest makefile Makefile.rhelver Kconfig.redhat redhat/ | tar -x

# Manually add hook instead of cherry-pick
# Add to middle to avoid git merge conflicts
# NOTE: commented out but left for future info to rebuild from scratch
# sed -i '/# We are using a recursive / i include Makefile.rhelver\n' Makefile

git add makefile Makefile.rhelver Makefile Kconfig.redhat redhat

git commit -m "bulk merge ark-infra as of $(date)"

echo
test "$TO_PUSH" && PUSH_VERB="Pushing" || PUSH_VERB="To push"
PUSH_STR="all release artifacts"
PUSH_CMD="git push gitlab ${BRANCH} && \\
	git push gitlab \"${RELEASE}\" && \\
	git push -f gitlab ark-latest && \\
	git push -f gitlab ark-infra
"

#Push branch
echo "# $PUSH_VERB $PUSH_STR"
echo "$PUSH_CMD"
test "$TO_PUSH" && eval "$PUSH_CMD"

exit 0
