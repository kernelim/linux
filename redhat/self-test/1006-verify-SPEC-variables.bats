#!/usr/bin/env bats
# Purpose: This test looks at the spec file variable replacement code in
# redhat/genspec.sh and confirms that each variable begins with "SPEC".

load test-lib.bash

_verify_SPEC_variables() {
# This looks at the code and replaces each / with a new-line character, removes
# any whitespace and entry entries beginning with valid "%%SPEC" or $"SPEC".
# "$SOURCES" lines are also okay as it is used to point to the changelog and
# the specfile.
awk '/# self-test begin/, /# self-test end/' $BATS_TEST_DIRNAME/../genspec.sh | grep -v "^#" | tr "/" "\n" | tr -d "\"" | sed -r '/^\s*$/d' | grep -v "%%SPEC" | grep -v "\$SPEC" | grep -v "\$SOURCES" | while read LINE
do
	echo $LINE
	case $(echo $LINE | xargs) in
	s) ;;
	d) ;;
	"sed -i -e") ;;
	*)
		echo " "
		echo "ERROR: Variables passed between genspec.sh and the spec file must begin with %%SPEC or \$SPEC."
		exit 1
		;;
	esac
done
}

@test "verify SPEC variables" {
	run _verify_SPEC_variables
	check_status
}
