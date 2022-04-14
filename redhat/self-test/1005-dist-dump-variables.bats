#!/usr/bin/env bats

function prologue()
{
    tag=$1
    ofile=$BATS_TMPDIR/$tag.out
    # Have to unset environment variables that may be inherited from supra-make:
    grep "^[ 	]*[a-zA-Z_][a-zA-Z_0-9]*[ 	]*[:?]*=" \
         $BATS_TEST_DIRNAME/../Makefile.common | \
        sed -e 's/[ 	]*\([a-zA-Z_][a-zA-Z_0-9]*\).*/unset \1/' | \
        sort | uniq > $BATS_TMPDIR/unset-vars.sh
    source $BATS_TMPDIR/unset-vars.sh
    GIT=$BATS_TEST_DIRNAME/egit.sh HEAD=$tag EGIT_OVERRIDE_DESCRIBE=$tag DIST=.fc33 make dist-dump-variables > $ofile
}

function checkversion()
{
    status=1
    if grep -x "_TAG=$1" $ofile && \
            grep -x "RPMKVERSION=$2" $ofile && grep -x "RPMKPATCHLEVEL=$3" $ofile && \
            grep -x "RPMKSUBLEVEL=$4" $ofile && grep -x "RPMKEXTRAVERSION=$5" $ofile && \
            grep -x "KEXTRAVERSION=$6" $ofile && \
            grep -x "SNAPSHOT=$7" $ofile
    then
        status=$?
    fi
}

@test "dist-dump-variables v5.8" {
    tag=v5.8
    prologue $tag
    checkversion $tag "5" "8" "0" "" "" "0"
    [ "$status" = 0 ]
}

@test "dist-dump-variables v5.8-rc7" {
    tag=v5.8-rc7
    prologue $tag
    checkversion $tag "5" "8" "0" "-rc7" ".rc7" "0"
    [ "$status" = 0 ]
}

@test "dist-dump-variables v5.8-9-g565674d613d7" {
    tag=v5.8-9-g565674d613d7
    prologue $tag
    checkversion $tag "5" "9" "0" "" ".rc0" "1"
    [ "$status" = 0 ]
}

@test "dist-dump-variables v5.8-rc5-99-g25ccd24ffd91" {
    tag=v5.8-rc5-99-g25ccd24ffd91
    prologue $tag
    checkversion $tag "5" "8" "0" "-rc5" ".rc5" "1"
    [ "$status" = 0 ]
}
