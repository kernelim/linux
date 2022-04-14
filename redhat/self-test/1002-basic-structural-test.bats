#!/usr/bin/env bats
@test "SRPM unpacks OK" {
    result=$(find "$BATS_TEST_DIRNAME"/.. -name "*.rpm" | wc -l)
    srpm=$(find "$BATS_TEST_DIRNAME"/.. -name "*.rpm")
    pushd "$BATS_TMPDIR"
    if [ -e SRPMS ]
    then
        rm -fr SRPMS
    fi
    mkdir SRPMS
    cd SRPMS
    rpm2cpio "$srpm" | cpio -idm
    status=$?
    [ "$status" = 0 ]
    popd >& /dev/null
}

@test "Linux tree unpacks OK" {
    pushd "$BATS_TMPDIR"/SRPMS >& /dev/null
    ls | wc
    linuxname=$(ls linux*.tar.xz)
    run tar --extract --xz -f "$linuxname"
    [ "$status" = 0 ]
    popd >& /dev/null
}

@test "Linux top level structural check" {
    pushd "$BATS_TMPDIR"/SRPMS >& /dev/null
    linuxtree=$(ls linux*.tar.xz)
    linuxtree=${linuxtree/.tar.xz}
    cd $linuxtree
    test -d arch	&& \
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
    status=$?
    popd >& /dev/null
    [ "$status" = 0 ]
}
