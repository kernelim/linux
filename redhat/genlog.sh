#!/bin/bash

LAST_MARKER=$(cat "${REDHAT}"/marker)
clogf="$1"
# hide [redhat] entries from changelog
HIDE_REDHAT=1;
# hide entries for unsupported arches
HIDE_UNSUPPORTED_ARCH=1;
# override LC_TIME to avoid date conflicts when building the srpm
LC_TIME=

GIT_FORMAT="--format=- %s (%an)%n%N%n^^^NOTES-END^^^%n%b"
GIT_NOTES="--notes=refs/notes/${RHEL_MAJOR}.${RHEL_MINOR}*"

lasttag=$(git rev-list --first-parent --grep="^\[redhat\] kernel-${SPECKVERSION}.${SPECKPATCHLEVEL}" --max-count=1 HEAD)
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
cversion="[$DISTBASEVERSION]";
echo "* $cdate $cname $cversion" > "$clogf"

git log --topo-order --no-merges -z "$GIT_NOTES" "$GIT_FORMAT" \
	^"${UPSTREAM}" "$lasttag".. -- ':!/redhat/rhdocs' | "${0%/*}"/genlog.py >> "$clogf"

if [ "$HIDE_REDHAT" = "1" ]; then
	grep -v -e "^- \[redhat\]" "$clogf" |
		sed -e 's!\[Fedora\]!!g' > "$clogf.tmp"
	mv -f "$clogf.tmp" "$clogf"
fi

if [ "$HIDE_UNSUPPORTED_ARCH" = "1" ]; then
	grep -E -v "^- \[(alpha|arc|arm|avr32|blackfin|c6x|cris|frv|h8300|hexagon|ia64|m32r|m68k|metag|microblaze|mips|mn10300|openrisc|parisc|score|sh|sparc|tile|um|unicore32|xtensa)\]" "$clogf" > "$clogf.tmp"
	mv -f "$clogf.tmp" "$clogf"
fi

# If the markers aren't the same then this a rebase.
# This means we need to zap entries that are already present in the changelog.
if [ "$MARKER" != "$LAST_MARKER" ]; then
	# genlog.py always adds a Resolves: line, thus we
	# can insert the rebase changelog item before it
	sed -i "s/\(^Resolves:.*\)/- Linux v${SPECVERSION}${UPSTREAMBUILD:+-}${UPSTREAMBUILD%.}\n\1/" "$clogf"
fi

# during rh-dist-git genspec runs again and generates empty changelog
# create empty file to avoid adding extra header to changelog
LENGTH=$(grep -c "^-" "$clogf" | awk '{print $1}')
if [ "$LENGTH" = 0 ]; then
	echo -n > "$clogf"
fi

echo "MARKER is $MARKER"
