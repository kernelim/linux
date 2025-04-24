#! /bin/bash

die()
{
	echo "$1"
	exit 1
}

ci_pre_check()
{
	if test -z "${GITLAB_PROJECT_URL}" || test -z "$GITLAB_PROJECT_PUSHURL"; then
                echo "To enable git-push, please run:"
		echo "git remote add gitlab <url>"
		echo "git remote set-url --push gitlab <pushurl>"
		if test -n "${TO_PUSH}"; then
			die "Misconfigured 'gitlab' entry for git"
		fi
        fi
        git diff-index --quiet HEAD || die "Dirty tree, please clean before merging."
}

# wrapper around branches that may not be exist yet
ark_git_branch()
{
	_target_branch="$1"
	_source_branch="$2"

	# switch to branch if it exists otherwise create and set to source
	# branch
	git show-ref -q --heads "$_target_branch" || \
		git branch "$_target_branch" "$_source_branch"
}

# GitLab can only mirror one project at a time.  This wrapper function does
# the mirroring for any other branches.
ark_git_mirror()
{
	target_branch="$1"
	upstream_tree="$2"
	source_branch="$3"
	reset_branch="$4"

	prev_branch="$(git rev-parse --abbrev-ref HEAD)"
	remote_branch="$upstream_tree/$source_branch"
	ark_git_branch "$target_branch" "$remote_branch"
	git checkout "$target_branch"
	git fetch "$upstream_tree" "$source_branch"
	if test -z "$reset_branch"; then
		git merge "$remote_branch" || die "git merge $remote_branch failed"
	else
		git reset --hard "$remote_branch" || die "git reset $remote_branch failed"
	fi
	git checkout "$prev_branch"
}

# Merge wrapper in case issues arise
ark_git_merge()
{
	target_branch="$1"
	source_branch="$2"

	prev_branch="$(git rev-parse --abbrev-ref HEAD)"
	ark_git_branch "$target_branch" "${source_branch}"
	git checkout "$target_branch"

	msg="Merge '${source_branch}' into '$target_branch'"
	if ! git merge -m "$msg" "${source_branch}"; then
		git merge --abort
		printf "Merge conflict; halting!\n"
		printf "To reproduce:\n"
		printf "* git checkout %s\n" "${target_branch}"
		printf "* git merge %s\n" "${source_branch}"
		die "Merge conflicts"
	fi

	git checkout "$prev_branch"
	return 0
}

ark_git_rebase()
{
	rebase_branch="$1"
	_upstream="$2"
	_base="$3"

	# GIT_SEQUENCE_EDITOR is used to filter out some commits
	# This requires interactive mode to work, so force it on.
	test -n "$GIT_SEQUENCE_EDITOR" && interactive=(-i) || interactive=()

	prev_branch="$(git rev-parse --abbrev-ref HEAD)"
	git checkout "${rebase_branch}"
	if ! git rebase "${interactive[@]}" --onto "$_base" "$_upstream"; then
		git rebase --abort
		printf "Rebase conflict; halting!\n"
		printf "To reproduce:\n"
		printf "* git checkout %s\n" "${rebase_branch}"
		printf "* git rebase --onto %s %s\n" "${_base}" "${_upstream}"
		die "Rebase conflicts"
	fi
	git checkout "$prev_branch"
	return 0
}

ark_update_configs()
{
	config_branch="$1"
	skip_configs="$2"

	prev_branch="$(git rev-parse --abbrev-ref HEAD)"
	git checkout "${config_branch}"

	# Generates and commits all the pending configs
	make -j FLAVOR=fedora dist-configs-commit
	# Skip executing gen_config_patches.sh for new Fedora configs

	old_head="$(git rev-parse HEAD)"
	make -j FLAVOR=rhel dist-configs-commit
	new_head="$(git rev-parse HEAD)"


	# Converts each new pending config from above into its finalized git
	# configs/<date>/<config> config_branch.  These commits are used for Merge
	# Requests.
	[ "$old_head" != "$new_head" ] && CONFIGS_ADDED="1" || CONFIGS_ADDED=""

	if test "$CONFIGS_ADDED"; then
		if test -z "$skip_configs"; then
			git checkout "$prev_branch"
			./redhat/scripts/genspec/gen_config_patches.sh "$config_branch"
		fi
	else
		printf "No new configuration values exposed from "
		printf "merging %s into $BRANCH\n" "$UPSTREAM_REF"
	fi

	git checkout "$prev_branch"
	test -z "$CONFIGS_ADDED" && return 0 || return 1
}

ark_push_changes()
{
	push_branch="$1"
	skip_configs="$2"

	prev_branch="$(git rev-parse --abbrev-ref HEAD)"
	git checkout "${push_branch}"

	TMPFILE=".push-warnings"
	touch "$TMPFILE"

	test "$ARK_REBASE" && FORCE=(-f) || FORCE=()
	test "$TO_PUSH" && PUSH_VERB="Pushing" || PUSH_VERB="To push"
	PUSH_STR="branch ${push_branch} to ${GITLAB_URL}"
	PUSH_CMD="git push ${FORCE[*]} gitlab ${push_branch}"
	PUSH_CONFIG_STR="config update branches"
	PUSH_CONFIG_CMD="for conf_branch in \$(git branch | grep configs/${push_branch}/\"\$(date +%F)\"); do
				git push \\
				-o merge_request.create \\
				-o merge_request.target=\"$push_branch\" \\
				-o merge_request.remove_source_branch \\
				gitlab \"\$conf_branch\" 2>&1 | tee -a $TMPFILE
				done
			 "

	#Push push_branch
	echo "# $PUSH_VERB $PUSH_STR"
	echo "$PUSH_CMD"
	test "$TO_PUSH" && eval "$PUSH_CMD"

	#Push config branches if created
	if test -z "$skip_configs"; then
		echo
		echo "# $PUSH_VERB $PUSH_CONFIG_STR"
		echo "$PUSH_CONFIG_CMD"
		test "$TO_PUSH" && eval "$PUSH_CONFIG_CMD"
	fi

	# GitLab server side warnings do not fail git-push but leave verbose
	# WARNING messages.  Grep for those and consider it a script
	# failure.  Make sure all push_branches are pushed first as follow up
	# git-pushes may succeed.
	grep -q "remote:[ ]* WARNINGS" "$TMPFILE" && die "Server side warnings"

	rm "$TMPFILE"
	git checkout "$prev_branch"
	return 0
}

# Common variables for all CI scripts
UPSTREAM_REF=${1:-"master"}
BRANCH=${2:-"os-build"}
PROJECT_ID=${PROJECT_ID:-"13604247"}
TO_PUSH=${DIST_PUSH:-""}
GITLAB_PROJECT_URL="$(git remote get-url gitlab 2>/dev/null)" || true
GITLAB_PROJECT_PUSHURL="$(git config --get remote.gitlab.pushurl 2>/dev/null)" || true

ci_pre_check

export UPSTREAM_REF
export BRANCH
export PROJECT_ID
export TO_PUSH
export GITLAB_PROJECT_URL
export GITLAB_PROJECT_PUSHURL
