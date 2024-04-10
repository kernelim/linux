#!/usr/bin/bash

# This script generates 'dist-dump-variables' output for various configurations
# using known ark commit IDs.  It uses this information as well as setting
# different values for DISTRO and DIST.
#
# The centos-stream-9 commit IDs are
#
#    edc9dd1e3c31 := 5.13.0 merge window (5.13 + additional changes before -rc1)
#    a5e13c6df0e4 := 5.12-rc5
#    9f4ad9e425a1 := 5.12
#    6161a435c191 := 5.12-rc5 + 2 additional commits
#

[ -z "${RHDISTDATADIR}" ] && echo "ERROR: RHDISTDATADIR undefined." && exit 1

# Store variables used in *this* script before unsetting them below.
destdir="${RHDISTDATADIR}"
# shellcheck disable=SC2153
sources="${SOURCES}"

# unset all redhat/Makefile variables so they do not interfere with make targets below
makefile_vars=$(make dist-dump-variables | grep "=" | cut -d"=" -f1)
while read -r VAR; do unset "$VAR"; done < <(echo "$makefile_vars")

specfile_helper () {
	local specfilename

	specfilename=$1
	cp ./kernel.spec.template "${varfilename}.spec.template"
	make RHSELFTESTDATA=1 SPECFILE="${specfilename}.spec" DIST="${DIST}" DISTRO="${DISTRO}" HEAD="${commit}" _setup-source
	grep -Fvx -f "${specfilename}.spec.template" "${sources}/${specfilename}.spec" > "${destdir}"/"${specfilename}".spec
	# Ignore bpftoolversion definition as it may change.
	sed -i '/^%define bpftoolversion /d' "${destdir}"/"${specfilename}".spec
	rm -f "${specfilename}.spec.template"
}

for DISTRO in fedora rhel centos
do
	for commit in edc9dd1e3c31 a5e13c6df0e4 9f4ad9e425a1 6161a435c191
	do
		for DIST in .fc25 .el7
		do
			varfilename="${DISTRO}-${commit}${DIST}"

			echo "building ${destdir}/$varfilename"

			# Ignored Makefile variables:
			# CURDIR is a make special target and cannot be easily changed.
			# UPSTREAM is the base merge commit and can change from day-to-day as
			# the tree is changed.
			# RHEL_RELEASE can change build-to-build.
			# SHELL can change depending on user's environment
			# BPFTOOLVERSION is derived from tools/lib/bpf/Makefile and may change.
			# RHGITURL may change depending on the user's method of cloning
			# RHDISTDATADIR will change based on these tests
			# VARS is a list of variables added for the 'dist-dump-variables' target
			# and can be ignored.
			make RHSELFTESTDATA=1 DIST="${DIST}" DISTRO="${DISTRO}" HEAD=${commit} dist-dump-variables | grep "=" |\
				grep -v -w CURDIR |\
				grep -v -w UPSTREAM |\
				grep -v -w RHEL_RELEASE |\
				grep -v -w SHELL |\
				grep -v -w BPFTOOLVERSION |\
				grep -v -w RHGITURL |\
				grep -v -w RHDISTDATADIR |\
				grep -v -w VARS |\
				sort -u >& "${destdir}/${varfilename}" &

			# shellcheck disable=SC2004
			waitpids[${count}]=$!
			((count++))

			echo "building ${destdir}/${varfilename}.spec"
			specfile_helper "${varfilename}" &
			# shellcheck disable=SC2004
			waitpids[${count}]=$!
			((count++))
		done

		# There isn't an easy way to make sure the parallel execution doesn't go crazy
		# and hammer a system.  Putting the wait loop here will artificially limit the
		# number of jobs.
		# shellcheck disable=SC2048
		for pid in ${waitpids[*]}; do
			wait "${pid}"
		done
	done
done

exit 0
