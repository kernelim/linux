#!/bin/bash
#
# Generate a changelog for a kernel rebuild package.
#
# When rebuilding the kernel for a separate package, the changelog should
# clearly indicate that this is a rebuild. This script fetches the previous
# changelog from dist-git, identifies new entries from the source kernel
# changelog, and prepends them along with a rebuild log entry.
#
# This is intended to be called from make dist-git which exports the required
# environment variables. To test standalone, pass the variables on the command
# line, e.g.:
#
#   REDHAT=$PWD/redhat TOPDIR=$PWD RHEL_MAJOR=10 RHEL_MINOR=2 \
#     SPECPACKAGE_NAME=kernel-automotive \
#     RHDISTGIT_BRANCH=c10s-sig-automotive-main \
#     RHPKG_BIN=centpkg-sig \
#     RHPKG_OPTS="--config $PWD/redhat/automotive-centpkg-sig.conf" \
#     RHPKG_NS=automotive/rpms/ \
#     DISTBASEVERSION=6.12.0-209.el10iv \
#     redhat/scripts/generate-rebuild-changelog.sh
#

set -e

# Since we don't commit the rebuild changelog to source-git,
# fetch the last changelog from dist-git.
fetch_distgit_clog() {
	local tmpdir="$1"
	local clog="$tmpdir/$SPECPACKAGE_NAME/${SPECPACKAGE_NAME}.changelog"
	# shellcheck disable=SC2086
	(
		cd "$tmpdir" &&
		eval $RHPKG_BIN $RHPKG_OPTS clone "${RHPKG_NS}${SPECPACKAGE_NAME}" &&
		cd "$SPECPACKAGE_NAME" &&
		$RHPKG_BIN switch-branch "$RHDISTGIT_BRANCH"
	) >/dev/null 2>&1 &&
	[[ -f "$clog" ]] && cat "$clog"
}

kernel_clog="${REDHAT}/kernel.changelog-${RHEL_MAJOR}.${RHEL_MINOR}"
pkg_clog="${REDHAT}/${SPECPACKAGE_NAME}.changelog-${RHEL_MAJOR}.${RHEL_MINOR}"

if [[ ! -f "$kernel_clog" ]]; then
	echo "Error: kernel changelog not found: $kernel_clog" >&2
	exit 1
fi

tmpdir=$(mktemp -d)
distgit_clog=$(mktemp)
trap 'rm -rf "$tmpdir" "$distgit_clog"' EXIT

if ! fetch_distgit_clog "$tmpdir" > "$distgit_clog"; then
	echo "Warning: could not fetch changelog from dist-git, assuming first build" >&2
	true > "$distgit_clog"
fi

# Find the last kernel version rebuilt by extracting the version from the first
# [version] header of our dist-git changelog, e.g. [6.12.0-209.el10].
last_synced=$(sed -n '/\[.*\]$/{s/.*\[\([^]]*\)\]$/\1/p;q;}' "$distgit_clog")

pkg_version="$DISTBASEVERSION"
HEAD="${HEAD:-HEAD}"

# Get the commit SHA for the rebuild reference
commit_sha=$(git rev-parse --short=12 "$HEAD")

# Assemble: rebuild entry combined with first kernel entry + remaining entries + previous changelog
{
	# Extract new entries from the kernel changelog.
	# Take everything since the last synced version.
	new_entries=$(mktemp)
	if [[ -n "$last_synced" ]]; then
		sed "/\[${last_synced}\]/,\$d" "$kernel_clog" > "$new_entries"
	else
		cat "$kernel_clog" > "$new_entries"
	fi

	# Create the rebuild entry
	# Example output:
	#   * Mon Apr 20 2026 Oleksii Baranov <olebaran@redhat.com> - 6.12.0-220.el10iv
	#   - Rebuild base kernel commit 5df0f425c0d3 for kernel-automotive
	#   - iommufd: Report ATS not supported status via IOMMU_GET_HW_INFO (Jerry Snitselaar) [RHEL-160188]
	#   Resolves: RHEL-160188
	cdate=$(LC_ALL=C date +"%a %b %d %Y")
	cname="$(git config user.name) <$(git config user.email)>"
	echo "* $cdate $cname - $pkg_version"
	echo "- Rebuild base kernel commit ${commit_sha} for ${SPECPACKAGE_NAME}"

	# Remove the first line starting with * (the kernel entry header) and keep everything else
	sed '0,/^\* /{ /^\* /d; }' "$new_entries"

	rm -f "$new_entries"

	# Append the changelog that we fetched from dist-git
	cat "$distgit_clog"
} > "$pkg_clog"

echo "Generated $pkg_clog"
