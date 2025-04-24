#!/bin/bash
#
# Download and install cross-compile tools if necessary.  If there is
# a cross-compiler already in the path, assume all is ready and there
# is nothing to do.
#
# In some cases, it may be necessary to download & install the latest
# EPEL7 repo information to get to the right packages.
#
# Argument(s) to this script is a list of rpm names to install.  If there
# is a value for the environment variable ARCH, we will use that, too.

# if there's already a cross-compiler specified, assume we're done
if [ "$ARCH" ]; then
	if [ "$CROSS_COMPILE" ]; then
		crossbin=$(whereis -b "$CROSS_COMPILE"gcc | cut -d: -f2 | cut -d' ' -f2)
		if [ "$crossbin" ]; then
			echo "Using $crossbin as the cross-compiler."
			exit 0
		else
			echo "Cross-compiler ${CROSS_COMPILE}gcc does not exist.  Standard cross-compiler"
			echo "packages will be used instead."
		fi
	fi
fi

# if we're not root, all we can do now is see what's installed
if [ "$(whoami)" != "root" ]; then
	echo "Checking for RHEL/Centos Stream cross compile packages.  If this fails, run \"make dist-cross-download\" as root."
	if rpm -q "$@" >& /dev/null; then
		echo "Compilers found."
		exit 0
	else
		echo "FAIL: Some packages are missing."
		exit 1
	fi
fi

# if everything is installed then exit successfully
rpm -q "$@" && exit 0

# install epel-release if necessary
dnf -y install /usr/lib/rpm/redhat/dist.sh

if [ -x /usr/lib/rpm/redhat/dist.sh ]; then
	dist=$(/usr/lib/rpm/redhat/dist.sh)
	# shellcheck disable=SC2081
	[ "$dist" == el* ] && dnf -y install epel-release
fi

# install list of rpms for cross compile
yum -y install "$@"

exit 0
