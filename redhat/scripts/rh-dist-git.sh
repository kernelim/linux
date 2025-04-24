#!/bin/bash

# clones and updates a dist-git repo

# shellcheck disable=SC2164

function die
{
	echo "Error: $1" >&2;
	exit 1;
}

function upload()
{
	[ -n "$RH_DIST_GIT_TEST" ] && return
	$RHPKG_BIN upload "$@" >/dev/null || die "uploading $*";
}

if [ -z "$RHDISTGIT_BRANCH" ]; then
	echo "$0: RHDISTGIT_BRANCH is not set" >&2
	exit 1
fi

echo "Cloning the repository"
# clone the dist-git, considering cache
date=$(date +"%Y-%m-%d")
tmpdir="$(mktemp -d --tmpdir="$RHDISTGIT_TMP" RHEL"$RHEL_MAJOR"."$date".XXXXXXXX)"
cd "$tmpdir" || die "Unable to create temporary directory";
test -n "$RHDISTGIT_CACHE" && reference="-- --reference $RHDISTGIT_CACHE"
echo "Cloning using $RHPKG_BIN" >&2;
# shellcheck disable=SC2086
eval $RHPKG_BIN clone "$SPECPACKAGE_NAME" "$reference" >/dev/null || die "Unable to clone using $RHPKG_BIN";
 
echo "Switching the branch"
# change in the correct branch
cd "$tmpdir/$SPECPACKAGE_NAME";
$RHPKG_BIN switch-branch "$RHDISTGIT_BRANCH" || die "switching to branch $RHDISTGIT_BRANCH";

echo "Unpacking from SRPM"
"$REDHAT"/scripts/expand_srpm.sh "$tmpdir"

# upload tarballs
sed -i "/linux-.*.tar.xz/d" "$tmpdir/$SPECPACKAGE_NAME"/{sources,.gitignore};
sed -i "/kernel-abi-stablelists.*.tar.xz/d" "$tmpdir/$SPECPACKAGE_NAME"/{sources,.gitignore};
sed -i "/kernel-kabi-dw-.*.tar.xz/d" "$tmpdir/$SPECPACKAGE_NAME"/{sources,.gitignore};
upload_list="$TARBALL $KABI_TARBALL $KABIDW_TARBALL"

echo "Uploading new tarballs: $upload_list"
# We depend on word splitting here:
# shellcheck disable=SC2086
upload $upload_list

echo "Creating diff for review ($tmpdir/diff) and changelog"
# diff the result (redhat/git/dontdiff). note: diff reuturns 1 if
# differences were found
diff -X "$REDHAT"/git/dontdiff -upr "$tmpdir/$SPECPACKAGE_NAME" "$REDHAT"/rpm/SOURCES/ > "$tmpdir"/diff;
# creating the changelog file

# changelog has been created by genspec.sh, including Resolves line, just copy it here
echo -e "${SPECPACKAGE_NAME}-${DISTBASEVERSION}\n" > "$tmpdir"/changelog
awk '1;/^Resolves: /{exit};' "$REDHAT"/"$SPECCHANGELOG" >> "$tmpdir"/changelog

# all done
echo "$tmpdir"
