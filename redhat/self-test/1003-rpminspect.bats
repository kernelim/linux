#!/usr/bin/env bats
# Purpose: This test runs rpminspect on the SRPM.

load test-lib.bash

@test "rpminspect" {
	if ! test -x /usr/bin/rpminspect; then
		skip "The rpminspect package is not installed"
	else
		skip "Skip rpminspect test pending fixes"
	fi

	numsrpms=$(find "$BATS_TEST_DIRNAME"/.. -name "*.src.rpm" | wc -l)
	if [ "$numsrpms" != "1" ]; then
		skip "Only one SRPM should be in $BATS_TEST_DIRNAME/redhat/rpms/SRPMS."
	fi

	srpm=$(find "$BATS_TEST_DIRNAME"/.. -name "*.src.rpm")
	run rpminspect $srpm
	check_status
}
