#!/usr/bin/env bats

function prologue()
{
    tag=$1
    ofile=$BATS_TMPDIR/$tag.out
    # Have to unset environment variables that may be inherited from supra-make:
    make dist-dump-variables | grep "=" | cut -d"=" -f1 | while read VAR; do unset "$VAR"; done
    GIT=$BATS_TEST_DIRNAME/egit.sh HEAD=$tag EGIT_OVERRIDE_DESCRIBE=$tag DIST=.fc33 make dist-dump-variables > $ofile
}

function checkversion()
{
	echo "verifying _TAG=$1"
	grep -E "^_TAG=$1" $ofile
	echo "verifying RPMKVERSION=$2"
	grep -E "^RPMKVERSION=$2" $ofile
	echo "verifying RPMPATCHLEVEL=$3"
	grep -E "^RPMKPATCHLEVEL=$3" $ofile
	echo "verifying RPMSUBLEVEL=$4"
	grep -E "^RPMKSUBLEVEL=$4" $ofile
	echo "verifying RPMEXTRAVERSION=$5"
	grep -E "^RPMKEXTRAVERSION=$5" $ofile
	echo "verifying KEXTRAVERSION=$6"
	grep -E "^KEXTRAVERSION=$6" $ofile
	echo "verifying SNAPSHOT=$6"
	grep -E "^SNAPSHOT=$7" $ofile
	status=0
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
