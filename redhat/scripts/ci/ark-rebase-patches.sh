#!/usr/bin/bash
#
# Automatically rebase the kernel patches in ark-patches.
#
# If the REPORT_BUGS environment variable is set, any patches that do not apply
# cleanly during the rebase are dropped, and an issue is filed to track rebasing
# that patch.
#
# If run with REPORT_BUGS, you must have python3-gitlab installed and a
# configuration file set up in ~/.python-gitlab.cfg or /etc/python-gitlab.cfg.
# An example configuration can be found at
# https://python-gitlab.readthedocs.io/en/stable/cli.html. If the configuration
# is not in one of the above locations, the path can be set
# with the PYTHON_GITLAB_CONFIG environment variable.
#
# Arguments:
#   1) The commit/tag/branch to rebase onto.
#   2) The Gitlab project ID to file issues against. See the project page on
#      Gitlab for the ID. For example, https://gitlab.com/cki-project/kernel-ark/
#      is project ID 13604247
set -e

UPSTREAM_REF=${1:-master}
test -n "$PROJECT_ID" || PROJECT_ID="${2:-13604247}"

ISSUE_TEMPLATE="During an automated rebase of ark-patches, commit %s failed to rebase.

The commit in question is:
~~~
%s
~~~

To fix this issue:

1. \`git rebase upstream ark-patches\`
2. Use your soft, squishy brain to resolve the conflict as you see fit. If it is
   non-trivial and has an \"Upstream Status: RHEL only\" tag, ask the author
   to rebase the patch.
3. \`if git tag -v $UPSTREAM_REF; then git branch ark/patches/$UPSTREAM_REF && git push upstream ark/patches/$UPSTREAM_REF; fi\`
4. \`git push -f upstream ark-patches\`
"

if [ -z "$PYTHON_GITLAB_CONFIG" ]; then
	GITLAB_CONFIG_OPT=""
else
	GITLAB_CONFIG_OPT="-c $PYTHON_GITLAB_CONFIG"
fi

# Check if ark-patches is already rebased to $UPSTREAM_REF
test -n "$(git branch os-build --contains "$UPSTREAM_REF")" && exit 0

if git show "$UPSTREAM_REF" > /dev/null 2>&1; then
	printf "Rebasing ark-patches onto %s...\n" "$UPSTREAM_REF"
else
	printf "No such git object \"%s\" in tree\n" "$UPSTREAM_REF"
	exit 1
fi

if [ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" -eq "$PROJECT_ID" ] 2> /dev/null; then
	printf "Filing issues against GitLab project ID %s\n" "$PROJECT_ID"
else
	printf "No Gitlab project ID specified; halting!\n"
	exit 1
fi

CLEAN_REBASE=true
if git rebase "$UPSTREAM_REF" ark-patches; then
	printf "Cleanly rebased all patches\n"
elif [ -n "$REPORT_BUGS" ]; then
	while true; do
		CLEAN_REBASE=false
		CONFLICT=$(git am --show-current-patch)
		COMMIT=$(git am --show-current-patch | head -n1 | awk '{print $2}' | cut -c 1-12)
		TITLE=$(printf "Unable to automatically rebase commit %s" "$COMMIT")
		# shellcheck disable=SC2059     # There is a multi-line pattern in ISSUE_TEMPLATE;
		# wiki says there is no good rewrite and recommends disabling warning.
		DESC=$(printf "$ISSUE_TEMPLATE" "$COMMIT" "$CONFLICT")
		# shellcheck disable=SC2086
		# GITLAB_CONFIG_OPT DEPENDS on word splitting:
		OPEN_ISSUES=$(gitlab $GITLAB_CONFIG_OPT project-issue list --project-id "$PROJECT_ID" --search "$TITLE")
		if [ -n "$OPEN_ISSUES" ]; then
			echo "Skipping filing an issue about commit $COMMIT; already exists as $OPEN_ISSUES"
			continue
		fi

		# shellcheck disable=SC2086
		# GITLAB_CONFIG_OPT DEPENDS on word splitting:
		if gitlab $GITLAB_CONFIG_OPT project-issue create --project-id "$PROJECT_ID" \
			--title "$TITLE" --description "$DESC" --labels "Patch Rebase"; then
			if git rebase --skip; then
				printf "Finished dropping patches that fail to rebase\n"
				break
			else
				continue
			fi
		else
			printf "Halting rebase because an issue cannot be filed for a conflict\n"
			exit 1
		fi
	done
else
	printf "A conflict occurred while rebase patches, please resolve manually.\n"
	exit 2
fi

if $CLEAN_REBASE; then
	if test -n "$DIST_PUSH"; then
		echo "Pushing branch ark-patches to $(git remote get-url gitlab)"
		git push -f gitlab ark-patches
	else
		printf "You can safely update ark-patches with 'git push -f <remote> ark-patches'\n"
	fi
else
	printf "Some patches could not be rebased, fix up ark-patches as necessary"
	printf " before pushing the branch."
	exit 2
fi

if git tag -v "$UPSTREAM_REF" > /dev/null 2>&1; then
	printf "Creating branch \"ark/patches/%s\"\n" "$UPSTREAM_REF"
	git branch ark/patches/"$UPSTREAM_REF"
	if test -n "$DIST_PUSH"; then
		echo "Pushing branch ark/patches to $(git remote get-url gitlab)"
		git push gitlab ark/patches/"$UPSTREAM_REF"
	else
		printf "Don't forget to run 'git push <remote> ark/patches/%s'\n" "$UPSTREAM_REF"
	fi
fi
