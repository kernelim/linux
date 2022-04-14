#!/bin/sh

# Adjusts the configuration options to build the variants correctly
#
# arg1: configuration to go in the primary variant
# arg2: are we only generating debug configs


PRIMARY=$1
DEBUGBUILDSENABLED=$2

if [ -z "$2" ]; then
	exit 1
fi

if [ -z "$PRIMARY" ]; then
	PRIMARY=rhel
fi

if [ "$PRIMARY" = "fedora" ]; then
	SECONDARY=rhel
else
	SECONDARY=fedora
fi

for i in kernel-*-"$PRIMARY".config; do
	NEW=kernel-"$VERSION"-$(echo "$i" | cut -d - -f2- | sed s/-"$PRIMARY"//)
	#echo $NEW
	mv "$i" "$NEW"
done

rm -f kernel-*-"$SECONDARY".config

if [ "$DEBUGBUILDSENABLED" -eq 0 ]; then
	for i in kernel-*debug*.config; do
		base=$(echo "$i" | sed -r s/-?debug//g)
		NEW=kernel-$(echo "$base" | cut -d - -f2-)
		mv "$i" "$NEW"
	done
fi
