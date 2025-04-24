#!/bin/bash
#
# This script is intended to regularly update the $BRANCH branch with the latest
# configuration options from upstream. It merges the given reference into
# $BRANCH, adds all new configuration symbols to the pending/ config directory,
# and creates a branch for each new config group.
#
# Arguments:
#   1) The git object to merge into $BRANCH. This should be something from
#	Linus's master branch, usually either a tag such as v5.5-rc3 or just
#	linus/master. The default is "master".
#   2) The Gitlab project ID to file issues against. See the project page on
#	Gitlab for the ID. For example, https://gitlab.com/cki-project/kernel-ark/
#	is project ID 13604247. The default is "13604247".

set -e

# source common CI functions and variables
# shellcheck disable=SC1091
. "$(dirname "$0")"/ark-ci-env.sh

finish()
{
	# shellcheck disable=SC2317
	rm "$TMPFILE"
}
trap finish EXIT

TMPFILE=".push-warnings"
touch $TMPFILE

git checkout "${BRANCH}"
if ! git merge -m "Merge '$UPSTREAM_REF' into '$BRANCH'" "$UPSTREAM_REF"; then
	git merge --abort
	printf "Merge conflict; halting!\n"
	die "Merge conflicts"
fi

# Generates and commits all the pending configs

make FLAVOR=fedora dist-configs-commit
# Skip executing gen_config_patches.sh for new Fedora configs

old_head="$(git rev-parse HEAD)"
make FLAVOR=rhel dist-configs-commit
new_head="$(git rev-parse HEAD)"

# check for config mismatches after setting configs in the commit step above
make dist-configs-check || die "Config mismatch detected"

# Converts each new pending config from above into its finalized git
# configs/<date>/<config> branch.  These commits are used for Merge
# Requests.
[ "$old_head" != "$new_head" ] && CONFIGS_ADDED="1" || CONFIGS_ADDED=""

if test "$CONFIGS_ADDED"; then
	./redhat/scripts/genspec/gen_config_patches.sh "${BRANCH}"
        PUSH_VERB="Pushing"
else
	printf "No new configuration values exposed from merging %s into $BRANCH\n" "$UPSTREAM_REF"
        PUSH_VERB="To push"
fi

echo
PUSH_STR="branch ${BRANCH} to ${GITLAB_PROJECT_URL}"
PUSH_CMD="git push gitlab ${BRANCH}"
PUSH_CONFIG_STR="config update branches"
PUSH_CONFIG_CMD="for branch in \$(git branch | grep configs/${BRANCH}/\"\$(date +%F)\"); do
	git push \\
		-o merge_request.create \\
		-o merge_request.target=\"$BRANCH\" \\
		-o merge_request.remove_source_branch \\
		gitlab \"\$branch\" 2>&1 | tee -a $TMPFILE
done
"

#Push branch
echo "# $PUSH_VERB $PUSH_STR"
echo "$PUSH_CMD"
test "$TO_PUSH" && eval "$PUSH_CMD"

#Push config branches if created
if test "$CONFIGS_ADDED"; then
	echo
	echo "# $PUSH_VERB $PUSH_CONFIG_STR"
	echo "$PUSH_CONFIG_CMD"
	test "$TO_PUSH" && eval "$PUSH_CONFIG_CMD"
fi

# GitLab server side warnings do not fail git-push but leave verbose
# WARNING messages.  Grep for those and consider it a script
# failure.  Make sure all branches are pushed first as follow up
# git-pushes may succeed.
grep -q "remote:[ ]* WARNINGS" $TMPFILE && die "Server side warnings"

exit 0
