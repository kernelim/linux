#!/bin/sh

# $1: git source tree directory
# $2: cloned tree
# $3: package name
# $4: name of srpm
# shellcheck disable=SC2034     # tree, redhat unused

tree="$1";
cloned="$2";
package_name="$3";
redhat="$1/redhat";
srpm="$4";

cd "$cloned/$package_name" || die "\"$cloned\" doesn't seem to have a dist-git clone";

# delete everything in the cloned tree to avoid having stale files
rm -r -- *

git reset HEAD -- sources
git checkout sources
echo "*.xz" > .gitignore
echo "*.bz2" >> .gitignore

# expand the srpm into the tree
rpm2cpio "$srpm" | cpio -idmv

git add -A

