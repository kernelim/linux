#!/usr/bin/env bats
# Purpose: This is a test that verifies that Makefile.variable variable
# declarations are all declared with "?="

load test-lib.bash

_Makefile_variable_declarations_1() {
	git grep "?=" $BATS_TEST_DIRNAME/../Makefile.variables | wc -l
}

_Makefile_variable_declarations_2() {
	git grep "?=" $BATS_TEST_DIRNAME/../Makefile | grep -v "\"?=" | wc -l
}

@test "Makefile variable declarations" {
	run _Makefile_variable_declarations_1
	if [ "$output" -eq 0 ]; then
		echo "Test failed: No ?= variables found in Makefile.variables"
		status=1
	fi
	check_status

	run _Makefile_variable_declarations_2
	if [ "$output" -ne 0 ]; then
		echo "Test failed: Makefile should not ?= declarations."
		status=1
	fi
	check_status
}
