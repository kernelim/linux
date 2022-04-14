#!/bin/sh

GITID=$1
TARBALL=$2
DIR=$3

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
	GITID_NORMALIZE=$(git log --max-count=1 --pretty=format:%H "$GITID")
	if [ "${GITID_NORMALIZE}" = "${TARID}" ]; then
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
  git archive --prefix="$DIR"/ --format=tar "$GITID" | xz $XZ_OPTIONS $XZ_THREADS > "$TARBALL";
