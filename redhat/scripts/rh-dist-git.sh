#!/bin/bash

# clones and updates a dist-git repo
# $1: branch to be used
# $2: local pristine clone of dist-git
# $3: alternate tmp directory (if you have faster storage)
# $4: alternate dist-git server
# $5: kernel source tarball
# $6: kabi stablelists tarball
# $7: dwarf-bases kabi tarball
# $8: zstream build
# $9: package name
# shellcheck disable=SC2164

rhdistgit_branch=$1;
rhdistgit_cache=$2;
rhdistgit_tmp=$3;
rhdistgit_tarball=$4;
rhdistgit_kabi_tarball=$5;
rhdistgit_kabidw_tarball=$6;
package_name=$7;
rpm_version=$8;
changelog=$9;
rhel_major=${10};
rhpkg_bin=${11};
srpm_name=${12};

redhat=$(dirname "$0")/..;
topdir="$redhat"/..;

function die
{
	echo "Error: $1" >&2;
	exit 1;
}

function upload()
{
	[ -n "$RH_DIST_GIT_TEST" ] && return
	$rhpkg_bin upload "$@" >/dev/null || die "uploading $*";
}

if [ -z "$rhdistgit_branch" ]; then
	echo "$0 <branch> [local clone] [alternate tmp] [alternate dist-git server]" >&2;
	exit 1;
fi

echo "Cloning the repository"
# clone the dist-git, considering cache
date=$(date +"%Y-%m-%d")
tmpdir="$(mktemp -d --tmpdir="$rhdistgit_tmp" RHEL"$rhel_major"."$date".XXXXXXXX)"
cd "$tmpdir" || die "Unable to create temporary directory";
test -n "$rhdistgit_cache" && reference="-- --reference $rhdistgit_cache"
echo "Cloning using $rhpkg_bin" >&2;
eval $rhpkg_bin clone "$package_name" "$reference" >/dev/null || die "Unable to clone using $rhpkg_bin";

echo "Switching the branch"
# change in the correct branch
cd "$tmpdir/$package_name";
$rhpkg_bin switch-branch "$rhdistgit_branch" || die "switching to branch $rhdistgit_branch";

echo "Copying updated files"
# copy the required files (redhat/git/files)
"$redhat"/scripts/expand_srpm.sh "$topdir" "$tmpdir" "$package_name" "$srpm_name";

echo "Uploading new tarballs"
# upload tarballs
sed -i "/linux-.*.tar.xz/d" "$tmpdir/$package_name"/{sources,.gitignore};
sed -i "/kernel-abi-stablelists.*.tar.bz2/d" "$tmpdir/$package_name"/{sources,.gitignore};
sed -i "/kernel-kabi-dw-.*.tar.bz2/d" "$tmpdir/$package_name"/{sources,.gitignore};
upload_list="$rhdistgit_tarball $rhdistgit_kabi_tarball $rhdistgit_kabidw_tarball"

# We depend on word splitting here:
# shellcheck disable=SC2086
upload $upload_list

echo "Creating diff for review ($tmpdir/diff) and changelog"
# diff the result (redhat/cvs/dontdiff). note: diff reuturns 1 if
# differences were found
diff -X "$redhat"/git/dontdiff -upr "$tmpdir/$package_name" "$redhat"/rpm/SOURCES/ > "$tmpdir"/diff;

# changelog has been created by genspec.sh, including Resolves line, just copy it here
echo -e "${package_name}-${rpm_version}\n" > $tmpdir/changelog
awk '1;/^Resolves: /{exit};' $changelog >> $tmpdir/changelog


# all done
echo "$tmpdir"
