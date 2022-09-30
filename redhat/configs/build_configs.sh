#!/bin/bash
#
# This script merges together the hierarchy of CONFIG_* files under generic
# and debug to form the necessary $PACKAGE_NAME<version>-<arch>-<variant>.config
# files for building RHEL kernels, based on the contents of a control file

PACKAGE_NAME="${1:-kernel}" # defines the package name used
SUBARCH="${2:-}" # defines a specific arch
SCRIPT=$(readlink -f "$0")
OUTPUT_DIR="$PWD"
SCRIPT_DIR=$(dirname "$SCRIPT")

if [ -z "$3" ]; then
	cat flavors > .flavors
else
	echo "$3" > .flavors
fi

RHJOBS="$(test -n "$4" && echo "$4" || nproc --all)"

LANG=en_US.UTF-8

# to handle this script being a symlink
cd "$SCRIPT_DIR"

set errexit
set nounset

cleanup()
{
	rm -f config-*
	rm -f .flavors
}

die()
{
	echo "$1"
	cleanup
	exit 1
}

function combine_config_layer()
{
	dir=$1
	file="config-${dir//\//-}"

	# shellcheck disable=SC2010
	if [ "$(ls "$dir"/ | grep -c "^CONFIG_")" -eq 0 ]; then
		touch "$file"
		return
	fi

	cat "$dir"/CONFIG_* > "$file"
}

function merge_configs()
{
	local archvar
	local arch
	local configs
	local order
	local flavor
	local count
	local name
	local skip_if_missing

	archvar=$1
	arch=$(echo "$archvar" | cut -f1 -d"-")
	configs=$2
	order=$3
	flavor=$4
	count=$5

	name=$OUTPUT_DIR/$PACKAGE_NAME-$archvar-$flavor.config
	echo "Building $name ... "
	touch config-merging.$count config-merged.$count

	# apply based on order
	skip_if_missing=""
	for o in $order
	do
		for config in ${configs//:/ }
		do
			cfile="config-$o-$config"

			test -n "$skip_if_missing" && test ! -e "$cfile" && continue

			if ! perl merge.pl "$cfile" config-merging.$count > config-merged.$count; then
				die "Failed to merge $cfile"
			fi
			mv config-merged.$count config-merging.$count
		done

		# first configs in $order is baseline, all files should be
		# there.  second pass is overrides and can be missing.
		skip_if_missing="1"
	done
	if [ "x$arch" == "xaarch64" ]; then
		echo "# arm64" > "$name"
	elif [ "x$arch" == "xppc64le" ]; then
		echo "# powerpc" > "$name"
	elif [ "x$arch" == "xs390x" ]; then
		echo "# s390" > "$name"
	elif [ "x$arch" == "xarmv7hl" ]; then
		echo "# arm" > "$name"
	elif [ "x$arch" == "xi686" ]; then
		echo "# i386" > "$name"
	else
		echo "# $arch" > "$name"
	fi
	sort config-merging.$count >> "$name"
	rm -f config-merged.$count config-merging.$count
	echo "Building $name complete"
}

function build_flavor()
{
	flavor=$1
	control_file="priority".$flavor
	while read -r line
	do
		if [ "$(echo "$line" | grep -c "^#")" -ne 0 ]; then
			continue
		elif [ "$(echo "$line" | grep -c "^$")" -ne 0 ]; then
			continue
		elif [ "$(echo "$line" | grep -c "^EMPTY")" -ne 0 ]; then
			empty=$(echo "$line" | cut -f2 -d"=")
			for a in $empty
			do
				echo "# EMPTY" > "$OUTPUT_DIR/$PACKAGE_NAME-$a-$flavor".config

			done
		elif [ "$(echo "$line" | grep -c "^ORDER")" -ne 0 ]; then
			order=$(echo "$line" | cut -f2 -d"=")
			for o in $order
			do
				glist=$(find "$o" -type d)
				for d in $glist
				do
					combine_config_layer "$d"
				done
			done
		else
			arch=$(echo "$line" | cut -f1 -d"=")
			configs=$(echo "$line" | cut -f2 -d"=")

			if [ -n "$SUBARCH" ]; then
				case $arch in
					$SUBARCH*)
						;;
					*)
						continue
				esac
			fi

			merge_configs "$arch" "$configs" "$order" "$flavor" "$count" &
			waitpids[$count]=$!
			((count++))
			while [ "$(jobs | grep Running | wc -l)" -ge $RHJOBS ]; do :; done
		fi
	done < "$control_file"

	for pid in ${waitpids[*]}; do
		wait $pid
	done
}

while read -r line
do
	build_flavor "$line"
done < .flavors

cleanup
