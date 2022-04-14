@test "shellcheck" {
    if ! test -x /usr/bin/shellcheck
    then
        skip "The ShellCheck package is not installed"
    fi
    run shellcheck $(find $BATS_TEST_DIRNAME/.. -name "*.sh")
    [ "$status" = 0 ]
}
