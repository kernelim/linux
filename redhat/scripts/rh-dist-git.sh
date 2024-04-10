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
	echo "$0 <branch> [local clone] [alternate tmp] [alternate dist-git server]" >&2;
	exit 1;
fi

echo "Cloning the repository"
# clone the dist-git, considering cache
date=$(date +"%Y-%m-%d")
tmpdir="$(mktemp -d --tmpdir="$RHDISTGIT_TMP" RHEL"$RHEL_MAJOR"."$date".XXXXXXXX)"
cd "$tmpdir" || die "Unable to create temporary directory";
test -n "$RHDISTGIT_CACHE" && reference="-- --reference $RHDISTGIT_CACHE"
echo "Cloning using $RHPKG_BIN" >&2;
eval "$RHPKG_BIN" clone "$PACKAGE_NAME" "$reference" >/dev/null || die "Unable to clone using $RHPKG_BIN";

echo "Switching the branch"
# change in the correct branch
cd "$tmpdir/$PACKAGE_NAME";
$RHPKG_BIN switch-branch "$RHDISTGIT_BRANCH" || die "switching to branch $RHDISTGIT_BRANCH";

echo "Copying updated files"
# copy the required files (redhat/git/files)
"$REDHAT"/scripts/expand_srpm.sh "$TOPDIR" "$tmpdir" "$PACKAGE_NAME" "$SRPM";

echo "Uploading new tarballs"
# upload tarballs
sed -i "/linux-.*.tar.xz/d" "$tmpdir/$PACKAGE_NAME"/{sources,.gitignore};
sed -i "/kernel-abi-stablelists.*.tar.bz2/d" "$tmpdir/$PACKAGE_NAME"/{sources,.gitignore};
sed -i "/kernel-kabi-dw-.*.tar.bz2/d" "$tmpdir/$PACKAGE_NAME"/{sources,.gitignore};
upload_list="$TARBALL $KABI_TARBALL $KABIDW_TARBALL"

# We depend on word splitting here:
# shellcheck disable=SC2086
upload $upload_list

echo "Creating diff for review ($tmpdir/diff) and changelog"
# diff the result (redhat/cvs/dontdiff). note: diff reuturns 1 if
# differences were found
diff -X "$REDHAT"/git/dontdiff -upr "$tmpdir/$PACKAGE_NAME" "$REDHAT"/rpm/SOURCES/ > "$tmpdir"/diff;
# creating the changelog file

# changelog has been created by genspec.sh, including Resolves line, just copy it here
echo -e "${PACKAGE_NAME}-${DISTBASEVERSION}\n" > "$tmpdir"/changelog
awk '1;/^Resolves: /{exit};' "$REDHAT"/"$SPECCHANGELOG" >> "$tmpdir"/changelog

# all done
echo "$tmpdir"
