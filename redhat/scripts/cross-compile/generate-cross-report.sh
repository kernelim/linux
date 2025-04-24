#!/bin/bash
#
# This script is called by the cross compile targets in redhat/Makefile.cross.
# The script outputs information for use by the maintainers to confirm that
# a build was completed.  The script output should be placed in the 0/1 header
# patch of a patch submission on RHKL.
#

echo "==============================================================================="
echo "                        CROSS COMPILE REPORT"
echo "==============================================================================="
echo "For patch submissions, this text must be cut-and-pasted into patch 0/1."
# satisfy patch verification scripts with a Build info line
echo "Build info: Cross compiled"
echo -n "Date: "
date

# Note, there is no guarantee that this environment is pristine.
echo -n "Build OS: "
cat /etc/redhat-release

# System name
echo -n "System name: "
HOSTNAME=$(hostname)

if [ -e ~/.rpmmacros ]; then
	if grep -q smp_mflags ~/.rpmmacros; then
		smpflags=$(awk -F " " ' { print $2 } ' ~/.rpmmacros )
		echo "$HOSTNAME with $smpflags"
	fi
else
	echo "$HOSTNAME"
fi

# Last known tag
lasttag=$(git describe --abbrev=0 --tags)
echo "Built on: $lasttag"

# Arches built?
# would have to be passed in on command line as string?
echo -n "Arch built: "
echo "$1"

# Was CROSS_COMPILE set to use non-standard compilers?
if [ "$CROSS_COMPILE" ]; then
	crossbin=$(whereis -b "$CROSS_COMPILE"gcc | cut -d: -f2 | cut -d' ' -f2)
	echo "==============================================================================="
	echo "For patch submissions, use only supported cross-compilers for testing."
	echo "CROSS_COMPILE set to: $CROSS_COMPILE"
else
	crossbin=$(whereis -b "$1"-linux-gnu-gcc | cut -d: -f2 | cut -d' ' -f2)
fi
test -x "$crossbin" && echo "Cross-compiler used: $crossbin"


echo "==============================================================================="
echo "For patch submissions this can optionally be included to show the changes"
echo "that were compiled into the tree."
echo "diffstat output (relative to $lasttag)"
git diff "$lasttag" | diffstat

echo "==============================================================================="
echo "==============================================================================="
