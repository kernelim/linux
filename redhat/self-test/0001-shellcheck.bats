#!/usr/bin/env bats
# Purpose: This test runs shellcheck on all .sh files in the redhat directory.

load test-lib.bash

@test "shellcheck" {
	if ! test -x /usr/bin/shellcheck; then
		skip "The ShellCheck package is not installed"
	fi
	run shellcheck $(find $BATS_TEST_DIRNAME/.. -name "*.sh" -not -path "$BATS_TEST_DIRNAME/../rpm/*" -not -path "$BATS_TEST_DIRNAME/../rhdocs/*")
	check_status
}
