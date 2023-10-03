#!/bin/bash
# SPDX-License-Identifier: GPL-2.0
# Copyright Red Hat
# author: Jiri Benc <jbenc@redhat.com>

set -e

function print_help
{
	{
	echo "Usage: $0 OPTIONS collection..."
	echo
	echo "Prepares the system to execute kernel selftests for the given collection(s)."
	echo "To list the available collections, run ./run_kselftest.sh -l. Alternatively,"
	echo "specify 'all' to prepare for all collections."
	echo
	echo "Options:"
	echo "  -s  safe modifications only"
	echo "  -m  load kernel modules; -s is implied"
	echo "  -d  destructive modifications; -m and -s is implied"
	echo
	echo "Note that if you use -d, your system will not be useful for anything else"
	echo "than the selftests afterwards."
	} >&2
	exit $1
}

# If you need to add a particular modification for a test collection, just
# add a new function with the name prepare_collection_safe,
# prepare_collection_modules and/or prepare_collection_destructive. The rest
# will be taken care of automatically. The - and / characters in collection
# names are translated to underscore. Beware that "set -e" is enabled.

function prepare_bpf_safe
{
	echo 1 > /proc/sys/net/mptcp/enabled
}

function prepare_bpf_modules
{
	modprobe nf_conntrack
	modprobe nf_nat
}

function prepare_bpf_destructive
{
	dnf install -y --allowerasing \
		https://kojipkgs.fedoraproject.org/packages/iptables/1.8.7/15.fc36/x86_64/iptables-libs-1.8.7-15.fc36.x86_64.rpm \
		https://kojipkgs.fedoraproject.org/packages/iptables/1.8.7/15.fc36/x86_64/iptables-legacy-libs-1.8.7-15.fc36.x86_64.rpm \
		https://kojipkgs.fedoraproject.org/packages/iptables/1.8.7/15.fc36/x86_64/iptables-legacy-1.8.7-15.fc36.x86_64.rpm
}

level=0
while getopts smdh opt; do
	case $opt in
	s) (( level > 1 )) || level=1 ;;
	m) (( level > 2 )) || level=2 ;;
	d) (( level > 3 )) || level=3 ;;
	h) print_help 0 ;;
	?) exit 1 ;;
	esac
done
shift $((OPTIND - 1))
[[ $# -gt 0 ]] || print_help 1
if (( level == 0 )); then
	echo "You must specify -s, -m or -d. See $0 -h for help." >&2
	exit 1
fi

if (( UID != 0 )); then
	echo "Please run this as root.">&2
	exit 1
fi

unset available
declare -A available
for func in $(compgen -A function); do
	[[ $func == prepare_* ]] || continue
	available[$func]=1
done

for component in "$@"; do
	# convert characters not valid in function names to _
	component=${component//[-\/]/_}
	if [[ $component == all ]]; then
		for func in "${!available[@]}"; do
			if [[ ( $func == *_safe && $level -ge 1 ) || \
			      ( $func == *_modules && $level -ge 2 ) || \
			      ( $func == *_destructive && $level -ge 3 ) ]]; then
				$func
			fi
		done
	else
		if [[ $level -ge 1 && ${available[prepare_${component}_safe]} ]]; then
			prepare_${component}_safe
		fi
		if [[ $level -ge 2 && ${available[prepare_${component}_modules]} ]]; then
			prepare_${component}_modules
		fi
		if [[ $level -ge 3 && ${available[prepare_${component}_destructive]} ]]; then
			prepare_${component}_destructive
		fi
	fi
done
