#!/usr/bin/env bats
@test "Exactly one SRPM exists" {
    result=$(find "$BATS_TEST_DIRNAME"/.. -name "*.rpm" | wc -l)
    [ "$result" = 1 ]
}

@test "rpminspect" {
    if ! test -x /usr/bin/rpminspect
    then
        skip "The rpminspect package is not installed"
    else
        skip "Skip rpminspect test pending fixes"
    fi
    srpm=$(find "$BATS_TEST_DIRNAME"/.. -name "*.rpm")
    run rpminspect $srpm
    [ "$status" = 0 ]
}
