#!/bin/bash
#
# generate-rebuild-changelog.sh - generate a changelog for a kernel rebuild package
#
# When a kernel is rebuilt as a separate package (e.g. kernel-automotive), its
# changelog must list the base kernel commits that went into the rebuild.  This
# script fetches the previous changelog from dist-git, determines which base
# kernel tags are new since the last rebuild, and produces a single changelog
# block with all the commits merged under one rebuild header.  The result is
# prepended to the existing dist-git changelog so that the full history is
# preserved in chronological order.
#
# The script handles two scenarios:
#
# 1) Rebuilding the next tag (+1)
#
#    The previous rebuild was kernel-6.12.0-231.el10 and the new rebuild is
#    kernel-6.12.0-232.el10.  The new changelog block contains only the commits
#    from tag 232:
#
#      * Wed Jun 03 2026 J. Doe <jdoe@redhat.com> - 6.12.0-232.el10iv
#      - Rebuild base kernel commit d3e637abf7ff for kernel-automotive
#      - Mon May 25 2026 CKI KWF Bot <bot@redhat.com> [6.12.0-232.el10]
#      - PCI: Fix alignment calculation ... [RHEL-151449]
#      - scsi: ses: Fix devices attaching ... [RHEL-153020]
#      Resolves: RHEL-151449, RHEL-153020
#
#      * Tue Jun 02 2026 J. Doe <jdoe@redhat.com> - 6.12.0-231.el10iv
#      - Rebuild base kernel commit 1d47564ebba9 for kernel-automotive
#      ...  (previous dist-git changelog, unchanged)
#
# 2) Skipping tags (+N, e.g. rebuilding 233 after 231)
#
#    Tags 232 and 233 were both released since the last rebuild.  Their commits
#    are merged into a single block and their Resolves lines are combined:
#
#      * Wed Jun 03 2026 J. Doe <jdoe@redhat.com> - 6.12.0-233.el10iv
#      - Rebuild base kernel commit 069b862c9daf for kernel-automotive
#      - Tue May 26 2026 CKI KWF Bot <bot@redhat.com> [6.12.0-233.el10]
#      - crypto: authenc - Correctly pass EINPROGRESS ... [RHEL-130557]
#      - Mon May 25 2026 CKI KWF Bot <bot@redhat.com> [6.12.0-232.el10]
#      - PCI: Fix alignment calculation ... [RHEL-151449]
#      Resolves: RHEL-130557, RHEL-151449
#
#      * Tue Jun 02 2026 J. Doe <jdoe@redhat.com> - 6.12.0-231.el10iv
#      ...  (previous dist-git changelog, unchanged)
#
#    The base kernel "* " headers are converted to "- " entries so they do
#    not create separate RPM changelog entries, keeping everything under the
#    single rebuild header in chronological order.  The first such "- " line
#    also serves as a version marker that the next rebuild uses to determine
#    last_synced tag name. In such way we ensure that the change log contains
#    only proper rebuilt tags.
#
#    Generally it is not recommended to use scenario 2 for rebuilds. Use the
#    first one instead.
#
#
# Called from make dist-git.  To test standalone:
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

# Determine the base kernel version from the previous rebuild.
# Primary: read from the "- <date> ... [version]" marker left by a prior run.
# Fallback: look up the git tag for the commit recorded in the rebuild line.
last_synced=$(sed -n '/^- .*\[[0-9][^]]*\]$/{s/.*\[\([^]]*\)\]$/\1/p;q;}' "$distgit_clog")

if [[ -z "$last_synced" ]]; then
	prev_commit=$(sed -n 's/^- Rebuild.*commit \([0-9a-f]*\) for .*/\1/p;T;q' "$distgit_clog")
	if [[ -n "$prev_commit" ]]; then
		tag=$(git tag --points-at "$prev_commit" 2>/dev/null \
			| grep '^kernel-' | head -1)
		[[ -n "$tag" ]] && last_synced="${tag#kernel-}"
	fi
fi

pkg_version="$DISTBASEVERSION"
HEAD="${HEAD:-HEAD}"
commit_sha=$(git rev-parse --short=12 "$HEAD")

# Build the new changelog block and prepend it to the existing dist-git changelog.
{
	# Extract kernel changelog entries since last_synced.  On first build
	# (last_synced empty), take only the newest tag's entries.
	new_entries=$(mktemp)
	if [[ -n "$last_synced" ]]; then
		sed "/\[${last_synced}\]/,\$d" "$kernel_clog" > "$new_entries"
	else
		awk '/^\* /{if(n++)exit}1' "$kernel_clog" > "$new_entries"
	fi

	# Merge all Resolves lines into one (relevant for +N rebuilds).
	resolves=$(grep '^Resolves:' "$new_entries" \
		| sed 's/^Resolves: *//' \
		| tr ',[:space:]' '\n' | sed '/^$/d; s/^ *//' | sort -u \
		| paste -sd, | sed 's/,/, /g')

	# Rebuild header
	cdate=$(LC_ALL=C date +"%a %b %d %Y")
	cname="$(git config user.name) <$(git config user.email)>"
	echo "* $cdate $cname - $pkg_version"
	echo "- Rebuild base kernel commit ${commit_sha} for ${SPECPACKAGE_NAME}"

	# Kernel entries: convert "* " headers to "- " (the first becomes a
	# version marker for the next rebuild), drop per-tag Resolves and blanks.
	sed 's/^\* /- /; /^Resolves:/d; /^$/d' "$new_entries"

	echo "Resolves: $resolves"
	rm -f "$new_entries"

	# Previous dist-git changelog, unchanged
	echo ""
	cat "$distgit_clog"
} > "$pkg_clog"

echo "Generated $pkg_clog"
