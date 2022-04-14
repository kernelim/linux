#!/bin/bash
#
# Arguments
#    SNAPSHOT: indicates whether or not this is based on an upstream tag. 1
#	indicates it is not, 0 indicates it is.

SOURCES=$1
SPECFILE=$2
CHANGELOG=$3
PKGRELEASE=$4
KVERSION=$5
KPATCHLEVEL=$6
KSUBLEVEL=$7
SPECRELEASE=$8
BUILDOPTS=$9
MARKER=${10}
LAST_MARKER=${11}
SINGLE_TARBALL=${12}
TARFILE_RELEASE=${13}
SNAPSHOT=${14}
UPSTREAM_BRANCH=${15}
INCLUDE_FEDORA_FILES=${16}
INCLUDE_RHEL_FILES=${17}
RHEL_MAJOR=${18}
RHEL_MINOR=${19}
BUILDID=${20}

RPMVERSION=${KVERSION}.${KPATCHLEVEL}.${KSUBLEVEL}
clogf="$SOURCES/changelog"
# hide [redhat] entries from changelog
HIDE_REDHAT=1;
# hide entries for unsupported arches
HIDE_UNSUPPORTED_ARCH=1;
# override LC_TIME to avoid date conflicts when building the srpm
LC_TIME=
# STAMP=$(echo $MARKER | cut -f 1 -d '-' | sed -e "s/v//"); # unused
RPM_VERSION="$RPMVERSION-$PKGRELEASE";

# We want to exclude changes in redhat/rhdocs tree from the changelog output.
# Since the redhat/rhdocs is a separate git subtree, we can exclude the full
# list of commits with "^" specifier against latest child from the subtree.
# This is done this way to be compatible with old git versions which do not
# have the pathspec '(exclude)' support
EXCLUDE=$(git log -1 --format=%P ${0%/*}/rhdocs | cut -d ' ' -f 2)

GIT_FORMAT="--format=- %s (%an)%n%N%n^^^NOTES-END^^^%n%b"
GIT_NOTES="--notes=refs/notes/${RHEL_MAJOR}.${RHEL_MINOR}*"

lasttag=$(git rev-list --first-parent --grep="^\[redhat\] kernel-${RPMVERSION}" --max-count=1 HEAD)
# if we didn't find the proper tag, assume this is the first release
if [[ -z $lasttag ]]; then
    if [[ -z ${MARKER//[0-9a-f]/} ]]; then
        # if we're doing an untagged release, just use the marker
        echo "Using $MARKER"
        lasttag=$MARKER
    else
	lasttag=$(git describe --match="$MARKER" --abbrev=0)
    fi
fi
echo "Gathering new log entries since $lasttag"
# master is expected to track mainline.

cname="$(git var GIT_COMMITTER_IDENT |sed 's/>.*/>/')"
cdate="$(LC_ALL=C date +"%a %b %d %Y")"
cversion="[$RPM_VERSION]";
echo "* $cdate $cname $cversion" > "$clogf"

UPSTREAM="$(git rev-parse -q --verify origin/$UPSTREAM_BRANCH || \
          git rev-parse -q --verify $UPSTREAM_BRANCH)"
 
git log --topo-order --no-merges -z $GIT_NOTES "$GIT_FORMAT" \
	^${UPSTREAM} ${EXCLUDE:+^$EXCLUDE} "$lasttag".. | ${0%/*}/genlog.py >> "$clogf"

if [ "$HIDE_REDHAT" = "1" ]; then
	grep -v -e "^- \[redhat\]" "$clogf" |
		sed -e 's!\[Fedora\]!!g' > "$clogf.stripped"
	cp "$clogf.stripped" "$clogf"
fi

if [ "$HIDE_UNSUPPORTED_ARCH" = "1" ]; then
	grep -E -v "^- \[(alpha|arc|arm|avr32|blackfin|c6x|cris|frv|h8300|hexagon|ia64|m32r|m68k|metag|microblaze|mips|mn10300|openrisc|parisc|score|sh|sparc|tile|um|unicore32|xtensa)\]" "$clogf" > "$clogf.stripped"
	cp "$clogf.stripped" "$clogf"
fi

# If the markers aren't the same then this a rebase.
# This means we need to zap entries that are already present in the changelog.
if [ "$MARKER" != "$LAST_MARKER" ]; then
	# awk trick to get all unique lines
	awk '!seen[$0]++' "$CHANGELOG" "$clogf" > "$clogf.unique"
	# sed trick to get the end of the changelog minus the line
	sed -e '1,/# END OF CHANGELOG/ d' "$clogf.unique" > "$clogf.tmp"
	# Add an explicit entry to indicate a rebase.
	echo "" > "$clogf"
	echo -e "- $MARKER rebase" | cat "$clogf.tmp" - >> "$clogf"
	rm "$clogf.tmp" "$clogf.unique"
fi

# HACK temporary hack until single tree workflow
# Don't reprint all the ark-patches again.
if [ -n "$(git log --oneline --first-parent --grep="Merge ark patches" "$lasttag"..)" ]; then
	# Throw away the clogf and just print the summary merge
	echo "" > "$clogf"
	echo "- Merge ark-patches" >> "$clogf"
fi

# during rh-dist-git genspec runs again and generates empty changelog
# create empty file to avoid adding extra header to changelog
LENGTH=$(grep "^-" $clogf | wc -l | awk '{print $1}')
if [ "$LENGTH" = 0 ]; then
	rm -f $clogf
	touch $clogf
fi

cat "$clogf" "$CHANGELOG" > "$clogf.full"
mv -f "$clogf.full" "$CHANGELOG"

# genlog.py generates Resolves lines as well, strip these from RPM changelog
cat $CHANGELOG | grep -v -e "^Resolves: " > $clogf.stripped

if [ "$SNAPSHOT" = 0 ]; then
	# This is based off a tag on Linus's tree (e.g. v5.5 or v5.5-rc5).
	# Two kernels are built, one with debug configuration and one without.
	DEBUG_BUILDS_ENABLED=1
else
	# All kernels are built with debug configurations.
	DEBUG_BUILDS_ENABLED=0
fi

if [ -n "$BUILDID" ]; then
	BUILDID_DEFINE=$(printf "%%define buildid %s" "$BUILDID")
else
	BUILDID_DEFINE="# define buildid .local"
fi

test -n "$SPECFILE" &&
        sed -i -e "
	/%%CHANGELOG%%/r $clogf.stripped
	/%%CHANGELOG%%/d
	s/%%BUILDID%%/$BUILDID_DEFINE/
	s/%%KVERSION%%/$KVERSION/
	s/%%KPATCHLEVEL%%/$KPATCHLEVEL/
	s/%%KSUBLEVEL%%/$KSUBLEVEL/
	s/%%PKGRELEASE%%/$PKGRELEASE/
	s/%%SPECRELEASE%%/$SPECRELEASE/
	s/%%DEBUG_BUILDS_ENABLED%%/$DEBUG_BUILDS_ENABLED/
	s/%%INCLUDE_FEDORA_FILES%%/$INCLUDE_FEDORA_FILES/
	s/%%INCLUDE_RHEL_FILES%%/$INCLUDE_RHEL_FILES/
	s/%%TARBALL_VERSION%%/$TARFILE_RELEASE/" "$SPECFILE"

echo "MARKER is $MARKER"

EXCLUDE_FILES=":(exclude,top).get_maintainer.conf \
		:(exclude,top).gitattributes \
		:(exclude,top).gitignore \
		:(exclude,top).gitlab-ci.yml \
		:(exclude,top)makefile \
		:(exclude,top)Makefile.rhelver \
		:(exclude,top)redhat \
		:(exclude,top)configs"

if [ "$SINGLE_TARBALL" = 0 ]; then
	# May need to preserve word splitting in EXCLUDE_FILES
	# shellcheck disable=SC2086
	git diff -p --no-renames --stat "$MARKER"..  $EXCLUDE_FILES \
		> "$SOURCES"/patch-"$RPMVERSION"-redhat.patch
else
	# Need an empty file for dist-git compatibility
	touch "$SOURCES"/patch-"$RPMVERSION"-redhat.patch
fi

# don't generate Patchlist.changelog file for RHEL

# We depend on work splitting of BUILDOPTS
# shellcheck disable=SC2086
for opt in $BUILDOPTS; do
	add_opt=
	[ -z "${opt##+*}" ] && add_opt="_with_${opt#?}"
	[ -z "${opt##-*}" ] && add_opt="_without_${opt#?}"
	[ -n "$add_opt" ] && sed -i "s/^\\(# The following build options\\)/%define $add_opt 1\\n\\1/" $SPECFILE
done

rm -f "$clogf"{,.stripped};
