#!/usr/bin/bash

# This script generates 'dist-dump-variables' output for various configurations
# using known ark commit IDs.  It uses this information as well as setting
# different values for DISTRO and DIST.
#
# The ark commit IDs are
#
#    78e36f3b0dae := 5.17.0 merge window (5.16 + additional changes before -rc1)
#    2585cf9dfaad := 5.16-rc5
#    df0cc57e057f := 5.16
#    fce15c45d3fb := 5.16-rc5 + 2 additional commits
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
	make RHSELFTESTDATA=1 SPECFILE="${specfilename}.spec" DIST="${DIST}" DISTRO="${DISTRO}" HEAD="${commit}" setup-source
	grep -Fvx -f "${specfilename}.spec.template" "${sources}/${specfilename}.spec" > "${destdir}"/"${specfilename}".spec
	# Ignore bpftoolversion definition as it may change.
	sed -i '/^%define bpftoolversion /d' "${destdir}"/"${specfilename}".spec
	rm -f "${specfilename}.spec.template"
}

for DISTRO in fedora rhel centos
do
	for commit in 78e36f3b0dae 2585cf9dfaad df0cc57e057f fce15c45d3fb
	do
		for DIST in .fc25 .el7
		do
			varfilename="${DISTRO}-${commit}${DIST}"

			echo "building ${destdir}/$varfilename"

			# Ignored Makefile variables:
                        # BUILD_TARGET changes every minor release
			# CURDIR is a make special target and cannot be easily changed.
			# UPSTREAM is the base merge commit and can change from day-to-day as
			# the tree is changed.
			# RHEL_RELEASE can change build-to-build.
			# DERIVATIVE_BUILD and DERIVATIVE_VERSION can change build-to-build.
			# SHELL can change depending on user's environment
			# RHGITURL may change depending on the user's method of cloning
			# RHDISTDATADIR will change based on these tests
			# VARS is a list of variables added for the 'dist-dump-variables' target
			# and can be ignored.
			make RHSELFTESTDATA=1 DIST="${DIST}" DISTRO="${DISTRO}" HEAD=${commit} dist-dump-variables | grep "=" |\
				grep -v -w BUILD_TARGET |\
				grep -v -w CURDIR |\
				grep -v -w DERIVATIVE_BUILD |\
				grep -v -w DERIVATIVE_VERSION |\
				grep -v -w UPSTREAM |\
				grep -v -w RHEL_RELEASE |\
				grep -v -w SHELL |\
				grep -v -w RHGITURL |\
				grep -v -w RHDISTDATADIR |\
				grep -v -w VARS |\
				sort -u >& "${destdir}/${varfilename}" && \
				sed -i 's/ \S*\(rhpkg.mk\)\S*//g' "${destdir}/${varfilename}" &

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
