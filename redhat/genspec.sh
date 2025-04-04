#!/bin/bash
# shellcheck disable=SC2153

UPSTREAM=$(git rev-parse -q --verify origin/"${UPSTREAM_BRANCH}" || \
	   git rev-parse -q --verify "${UPSTREAM_BRANCH}")

if [ "$SNAPSHOT" = 0 ]; then
	# This is based off a tag on Linus's tree (e.g. v5.5 or v5.5-rc5).
	# Two kernels are built, one with debug configuration and one without.
	SPECDEBUG_BUILDS_ENABLED=1
else
	# All kernels are built with debug configurations.
	SPECDEBUG_BUILDS_ENABLED=0
fi

if [ -n "$DISTLOCALVERSION" ]; then
	SPECBUILDID=$(printf "%%define buildid %s" "$DISTLOCALVERSION")
else
	SPECBUILDID="# define buildid .local"
fi

# The SPECRELEASE variable uses the SPECBUILDID variable which is
# defined above.  IOW, don't remove SPECBUILDID ;)
SPECRELEASE="${UPSTREAMBUILD}""${BUILD}""%{?buildid}%{?dist}"

EXCLUDE_FILES=":(exclude,top).get_maintainer.conf \
		:(exclude,top).gitattributes \
		:(exclude,top).gitignore \
		:(exclude,top).gitlab-ci.yml \
		:(exclude,top)makefile \
		:(exclude,top)Makefile.rhelver \
		:(exclude,top)redhat \
		:(exclude,top)configs"

# If PATCHLIST_URL is not set to "none", generate Patchlist.changelog file that
# holds the shas and commits not included upstream and git commit url.
SPECPATCHLIST_CHANGELOG=0
if [ "$PATCHLIST_URL" != "none" ]; then
	# sed convert
	# <sha> <description>
	# to
	# <ark_commit_url>/<sha>
	#  <sha> <description>
	#
	# May need to preserve word splitting in EXCLUDE_FILES
	# shellcheck disable=SC2086
	git log --no-merges --pretty=oneline --no-decorate ${UPSTREAM}.. $EXCLUDE_FILES | \
		sed "s!^\([^ ]*\)!$PATCHLIST_URL/\1\n &!; s!\$!\n!" \
		> "$SOURCES"/Patchlist.changelog
	SPECPATCHLIST_CHANGELOG=1
fi

# self-test begin
test -f "$SOURCES/$SPECFILE" &&
	sed -i -e "
	s/%%SPECBUILDID%%/$SPECBUILDID/
	s/%%SPECKVERSION%%/$SPECKVERSION/
	s/%%SPECKPATCHLEVEL%%/$SPECKPATCHLEVEL/
	s/%%SPECBUILD%%/$SPECBUILD/
	s/%%SPECRELEASE%%/$SPECRELEASE/
	s/%%SPECDEBUG_BUILDS_ENABLED%%/$SPECDEBUG_BUILDS_ENABLED/
	s/%%SPECINCLUDE_FEDORA_FILES%%/$SPECINCLUDE_FEDORA_FILES/
	s/%%SPECINCLUDE_RHEL_FILES%%/$SPECINCLUDE_RHEL_FILES/
	s/%%SPECPATCHLIST_CHANGELOG%%/$SPECPATCHLIST_CHANGELOG/
	s/%%SPECVERSION%%/$SPECVERSION/
	s/%%SPECKABIVERSION%%/$SPECKABIVERSION/
	s/%%SPECTARFILE_RELEASE%%/$SPECTARFILE_RELEASE/" "$SOURCES/$SPECFILE"
test -n "$RHSELFTESTDATA" && test -f "$SOURCES/$SPECFILE" && sed -i -e "
	/%%SPECCHANGELOG%%/r $SOURCES/$SPECCHANGELOG
	/%%SPECCHANGELOG%%/d" "$SOURCES/$SPECFILE"
# self-test end

# We depend on work splitting of BUILDOPTS
# shellcheck disable=SC2086
for opt in $BUILDOPTS; do
	add_opt=
	[ -z "${opt##+*}" ] && add_opt="_with_${opt#?}"
	[ -z "${opt##-*}" ] && add_opt="_without_${opt#?}"
	[ -n "$add_opt" ] && sed -i "s/^\\(# The following build options\\)/%define $add_opt 1\\n\\1/" "$SOURCES/$SPECFILE"
done

# The self-test data doesn't currently have tests for the changelog or patch file, so the
# rest of the script can be ignored.  See redhat/Makefile setup-source target for related
# test changes.
if [ -n "$RHSELFTESTDATA" ]; then
	exit 0
fi

clogf=$(mktemp)
trap 'rm -f "$clogf" "$clogf".stripped' SIGHUP SIGINT SIGTERM EXIT
"${0%/*}"/genlog.sh "$clogf"

cat "$clogf" "$SOURCES/$SPECCHANGELOG" > "$clogf.full"
mv -f "$clogf.full" "$SOURCES/$SPECCHANGELOG"

# genlog.py generates Resolves lines as well, strip these from RPM changelog
grep -v -e "^Resolves: " "$SOURCES/$SPECCHANGELOG" > "$clogf".stripped

test -f "$SOURCES/$SPECFILE" &&
	sed -i -e "
	/%%SPECCHANGELOG%%/r $clogf.stripped
	/%%SPECCHANGELOG%%/d" "$SOURCES/$SPECFILE"

if [ "$DISTRO" == "fedora" ]; then
	# The tarball in the SRPM contains only the upstream sources.

	# May need to preserve word splitting in EXCLUDE_FILES
	# shellcheck disable=SC2086
	git diff -p --binary --no-renames --stat "$MARKER".. $EXCLUDE_FILES \
		> ${SOURCES}/patch-${SPECKVERSION}.${SPECKPATCHLEVEL}-redhat.patch
else
	# The tarball in the SRPM contains both upstream sources and OS-specifc
	# commits.  Even though this is the case, an empty file for dist-git
	# compatibility is necessary.
	touch "${SOURCES}/patch-${SPECKVERSION}.${SPECKPATCHLEVEL}"-redhat.patch
fi
