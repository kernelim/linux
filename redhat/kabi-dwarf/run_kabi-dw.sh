#!/bin/sh
# Copyright(C) 2017, Red Hat, Inc., Stanislav Kozina
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Simple wrapper around the kabi-dw tool
# The purpose of the script is to ensure we can call the kabi-dw using the
# same options from both the Makefile and kernel.spec file.
#
# Usage:
# 	./run_kabi-dw.sh generate stablelist module_dir kabi_dir
# 	./run_kabi-dw.sh compare kabi_dir1 kabi_dir2
# shellcheck disable=SC2164

DIR=$(dirname "$0")
DIR=$(cd "$DIR"; pwd)
PROG="$0"

KABIDW=kabi-dw

usage() {
	echo "Usage:"
	echo "	$PROG generate stablelist module_dir kabi_dir"
	echo "	$PROG compare kabi_dir1 kabi_dir2"
	exit 1
}

generate() {
	if [ $# != 4 ]; then
		usage
	fi
	WHITELIST=$2
	SRC=$3
	DST=$4

	if [ -d "$DST" ]; then \
		rm -rf "$DST"
	fi

	${KABIDW} generate -r -s "$WHITELIST" -o "$DST" "$SRC"
}

compare() {
	if [ $# != 3 ]; then
		usage
	fi
	A="$2"
	B="$3"
	${KABIDW} compare -k "$A" "$B"
}

if [ $# -lt 1 ]; then
	usage
fi

case "$1" in
    generate )
	generate "$@"
        ;;
    compare )
        compare "$@"
        ;;
    * )
        usage
        ;;
esac
