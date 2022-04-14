#!/bin/bash

# Clones a RHEL dist-git tree using a local reference if existent
# $1: repository
# $2: local clone
# $3: use a different tmp directory (for people with SSDs)
# $4: package name

repo="$1";
local="$2";
tmp_dir="$3";
package_name="$4";
rhel_major="$5";
rhpkg_bin="$6";

function die
{
	echo "Error: $1" >&2;
	exit 1;
}

date=$(date +"%Y-%m-%d")
tmp="$(mktemp -d --tmpdir="$tmp_dir" RHEL"$rhel_major"."$date".XXXXXXXX)";
cd "$tmp" || die "Unable to create temporary directory";

if [[ -n $repo && -n $local ]]; then
	git clone --reference "$local" "$repo" "$package_name" >/dev/null || die "Unable to clone using local cache";
	# if there're tarballs present that are listed in the "sources" file,
	# copy them or it'll be downloaded again
	if [ -e "$local/sources" ]; then
		while IFS= read -r i; do
			if [ -f "$local/$i" ]; then
				cp "$local/$i" "$tmp/kernel/";
			fi
		done < "$local"/sources
	fi
else
	echo "No local repo, cloning using $rhpkg_bin" >&2;
	$rhpkg_bin clone "$package_name" >/dev/null || die "Unable to clone using $rhpkg_bin";
fi

echo "$tmp";

