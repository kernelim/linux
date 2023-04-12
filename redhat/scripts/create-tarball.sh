#!/bin/sh

# shellcheck disable=SC2153
[ "$DISTRO" != "fedora" ] && _GITID="$GITID" || _GITID="$MARKER"

# shellcheck disable=SC1083
XZ_THREADS=$(rpm --eval %{_smp_mflags} | sed -e 's!^-j!--threads !')

ARCH=$(arch)
XZ_OPTIONS=""

if [ "$ARCH" != "x86_64" ]
then
        XZ_OPTIONS="-M 3G"
fi

if [ -f "$TARBALL" ]; then
	TARID=$(xzcat -qq "$TARBALL" | git get-tar-commit-id 2>/dev/null)
	if [ "$_GITID" = "$TARID" ]; then
		echo "$(basename "$TARBALL") unchanged..."
		exit 0
	fi
	rm -f "$TARBALL"
fi

echo "Creating $(basename "$TARBALL")..."
trap 'rm -vf "$TARBALL"' INT
# XZ_OPTIONS and XZ_THREADS DEPEND on word splitting, so don't disable it here:
# shellcheck disable=SC2086
cd ../ &&
  git archive --prefix="linux-$SPECTARFILE_RELEASE"/ --format=tar "$_GITID" | xz $XZ_OPTIONS $XZ_THREADS > "$TARBALL";
