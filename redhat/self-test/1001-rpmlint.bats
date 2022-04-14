#!/usr/bin/env bats
@test "Exactly one SRPM exists" {
    result=$(find "$BATS_TEST_DIRNAME"/.. -name "*.rpm" | wc -l)
    [ "$result" = 1 ]
}

@test "rpmlint" {
    if ! test -x /usr/bin/rpmlint
    then
        skip "The rpmlint package is not installed"
    else
        skip "Skip rpmlint test pending kernel.spec.template changes"
    fi
    srpm=$(find "$BATS_TEST_DIRNAME"/.. -name "*.rpm")
    run rpmlint $srpm
    [ "$status" = 0 ]
}
