#!/bin/bash
set -e

function in_names()
{
	local name
	for name in "${names[@]}"; do
		[[ $1 != "$name" ]] || return 0
	done
	return 1
}

if ! git rev-parse --verify main >& /dev/null; then
	git fetch origin main
	git branch --track main origin/main
fi
IFS=$'\n' names=($(git diff --name-only main))
if in_names info/owners.yaml; then
	for name in "${names[@]}"; do
		[[ $name != info/owners.yaml && $name != info/RHMAINTAINERS &&
		   $name != info/CODEOWNERS ]] || continue
		echo "======================================================="
		echo "These changes include owners.yaml modifications together with other"
		echo "changes.  As a safeguard against mistakes, this is not allowed."
		echo
		echo "If you need to do infrastructure changes please submit two separate"
		echo "merge requests, one for owners.yaml and one for the rest."
		echo "======================================================="
		exit 1
	done
fi
if in_names info/owners.yaml && \
	test "$(git config --get owners.warning)" != "false"; then
	echo "======================================================="
	echo "These changes include owners.yaml modifications.  Please"
	echo "review these Merge Request Approval Rules.  The Merge Request"
	echo "author must add the appropriate engineers as reviewers on"
	echo "the submitted documentation project Merge Request."
	echo " "
	echo "* Included and excluded file changes can be merged if the"
	echo "MR author is a subsystem maintainer. If the author is not a"
	echo "subsystem maintainer, then the subsystem maintainer must"
	echo "provide an approve."
	echo " "
	echo "* Any MR adding an engineer in a role must be authored by"
	echo "or approved by the added engineer. An additional approve from a"
	echo "subsystem maintainer is required, unless the maintainer is the"
	echo "author of the MR."
	echo " "
	echo "* Any MR removing an engineer in a role must be authored by"
	echo "or approved by the removed engineer, except in the case when"
	echo "the removed engineer is no longer with Red Hat. While removals"
	echo "from roles do not require the approve of the maintainer, MR"
	echo "authors are encouraged to add the maintainer for an approve."
	echo " "
	echo "* Any MR adding or modifying a devel-sst field requires the"
	echo "approval from the subsystem maintainer."
	echo " "
	echo "This warning can be disabled by executing:"
	echo "        git config --add owners.warning false"
	echo "======================================================="
fi
if test -n "$(git diff main | grep "^+" | grep "\s\- rhel-sst-null" )"; then
	echo "ERROR: New entries cannot set devel-sst to rhel-sst-null."
	exit 1
fi
if in_names scripts/validSSTNames.go && \
	test "$(git config --get validsstnames.warning)" != "false"; then
	echo "======================================================="
	echo "These changes include validSSTNames.go changes.  You must ensure"
	echo "the SST names themselves, and the SST name changes in the file are"
	echo "approved by RHEL management.  Changes to this file that have"
	echo "not been verified by management will be removed by reverting commits."
	echo " "
	echo "This warning can be disabled by executing:"
	echo "        git config --add validsstnames.warning false"
	echo "======================================================="
fi
exit 0
