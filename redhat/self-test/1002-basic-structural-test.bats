#!/usr/bin/env bats
# Purpose: This test runs tests on the SRPM.

load test-lib.bash

_SRPM_unpacks_OK() {
	rpm2cpio "$srpm" | cpio -idm
}

@test "SRPM unpacks OK" {
	numsrpms=$(find "$BATS_TEST_DIRNAME"/.. -name "*.src.rpm" | wc -l)
	if [ "$numsrpms" != "1" ]; then
		skip "Only one SRPM should be in $BATS_TEST_DIRNAME/redhat/rpms/SRPMS."
	fi

	srpm=$(find "$BATS_TEST_DIRNAME"/.. -name "*.src.rpm")
	pushd "$BATS_TMPDIR"
	if [ -e SRPMS ]; then
		rm -fr SRPMS
	fi
	mkdir SRPMS
	cd SRPMS
	run _SRPM_unpacks_OK
	check_status
	popd >& /dev/null
}

@test "Linux tree unpacks OK" {
numsrpms=$(find "$BATS_TEST_DIRNAME"/.. -name "*.src.rpm" | wc -l)
	if [ "$numsrpms" != "1" ]; then
		skip "Only one SRPM should be in $BATS_TEST_DIRNAME/redhat/rpms/SRPMS."
	fi

	pushd "$BATS_TMPDIR"/SRPMS >& /dev/null
	ls | wc
	linuxname=$(ls linux*.tar.xz)
	run tar --extract --xz -f "$linuxname"
	check_status
	popd >& /dev/null
}

@test "Linux top level structural check" {
	numsrpms=$(find "$BATS_TEST_DIRNAME"/.. -name "*.src.rpm" | wc -l)
	if [ "$numsrpms" != "1" ]; then
		skip "Only one SRPM should be in $BATS_TEST_DIRNAME/redhat/rpms/SRPMS."
	fi

	pushd "$BATS_TMPDIR"/SRPMS >& /dev/null
	linuxtree=$(ls linux*.tar.xz)
	linuxtree=${linuxtree/.tar.xz}
	cd $linuxtree
	run test -d arch	&& \
	test -d block	&& \
	test -d certs	&& \
	test -d crypto	&& \
	test -d Documentation	&& \
	test -d drivers	&& \
	test -d fs		&& \
	test -d include	&& \
	test -d init	&& \
	test -d ipc		&& \
	test -d kernel	&& \
	test -d lib
	test -d LICENSES	&& \
	test -d mm		&& \
	test -d net		&& \
	test -d samples	&& \
	test -d scripts	&& \
	test -d security	&& \
	test -d sound	&& \
	test -d tools	&& \
	test -d usr		&& \
	test -d virt
	check_status
	popd >& /dev/null
}
