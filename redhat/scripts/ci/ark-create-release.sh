#!/bin/bash
#
# Generate a release tag and, if based on a tagged upstream release, a set
# of release branches. This script will rebase the ark-patches branch, update
# os-build with the latest configurations, and apply any merge requests labeled
# with "Include in Releases".

set -e

UPSTREAM_REF=${1-master}
PROJECT_ID=${2:-13604247}

# Detect if there's one or more prior releases for this upstream ref.
if git describe "$UPSTREAM_REF" | grep -q -c '\-g'; then
	SHORT_COMMIT=$(git describe "$UPSTREAM_REF" | cut -d "g" -f 2)
	BASE_RELEASE=$(git tag -l | grep "$SHORT_COMMIT" | tail -n 1)
else
	if git describe "$UPSTREAM_REF" | grep -q -c "\-"; then
		RC_LEVEL="0.$(git describe "$UPSTREAM_REF" | cut -d "-" -f 2)"
		VERSION=$(git describe "$UPSTREAM_REF" | cut -d "-" -f 1 | cut -c 2-)
	else
		RC_LEVEL=""
		VERSION=$(git describe "$UPSTREAM_REF" | cut -c 2-)
	fi
	BASE_RELEASE=$(git tag -l | grep -E "kernel-$VERSION\.0-$RC_LEVEL\.[0-9]+" | tail -n 1)
fi
if [ -n "$BASE_RELEASE" ]; then
	printf "There's already a release for %s (tagged as %s); if you're trying \
		to create a new release check out that tag, apply any commits you \
		want, and then run \"touch localversion && make dist-release && make \
		dist-release-tag\".\n" "$UPSTREAM_REF" "$BASE_RELEASE"
	exit 3
fi

git checkout os-build
touch localversion
make dist-release

if git tag -v "$UPSTREAM_REF" > /dev/null 2>&1; then
	git checkout -b ark/"$UPSTREAM_REF" ark/patches/"$UPSTREAM_REF"
	RELEASE_BRANCHES=" ark/$UPSTREAM_REF ark/patches/$UPSTREAM_REF"
else
	# This is a snapshot release so we're only going to make a tag
	git checkout --detach os-build && git describe
	RELEASE_BRANCHES=""
fi
MR_PATCHES=$(gitlab project-merge-request list --project-id="$PROJECT_ID" \
	--labels="Include in Releases" --state=opened | grep -v "^$" | sort | \
	awk '{ print "https://gitlab.com/cki-project/kernel-ark/-/merge_requests/" $2 ".patch" }')
for patch_url in $MR_PATCHES; do
	curl -sL "$patch_url" | git am
done

make dist-release
make dist-release-tag
RELEASE=$(git describe)
git checkout ark-latest
git reset --hard "$RELEASE"

# Update ark-infra branch
git checkout ark-infra

# Using ark-latest because it has latest fixes
rm -rf makefile Makefile.rhelver redhat/
git archive --format=tar ark-latest makefile Makefile.rhelver redhat/ | tar -x

# Manually add hook instead of cherry-pick
# Add to middle to avoid git merge conflicts
# NOTE: commented out but left for future info to rebuild from scratch
# sed -i '/# We are using a recursive / i include Makefile.rhelver\n' Makefile

git add makefile Makefile.rhelver Makefile redhat
# Future rebuid note, .gitkeep files are gitignored and need force adding
# git add -f redhat/kabi/kabi-module/kabi*

git commit -m "bulk merge ark-infra as of $(date)"

printf "All done!

To push all the release artifacts, run:

git push os-build
for branch in \$(git branch | grep configs/\"\$(date +%%F)\"); do
\tgit push -o merge_request.create -o merge_request.target=os-build\
 -o merge_request.remove_source_branch upstream \"\$branch\"
done
git push upstream %s%s
git push -f upstream ark-latest\n" "$RELEASE" "$RELEASE_BRANCHES"
