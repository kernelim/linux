#!/usr/bin/bash

# This function makes use of bats built-in run function and its status and output variables.
check_status() {
	if [ "$status" -eq 0 ]; then
		return 0
	fi

	# report the error
	echo "$output"
	echo "------------------"
	expath=$(echo "$BATS_TEST_FILENAME" | rev | cut -d'/' -f-3 | rev)
	echo -n "This redhat/self-test test has failed.  You can run all tests by executing 'make dist-self-test', or just this test by executing 'bats $expath'."
	exit 1
}

