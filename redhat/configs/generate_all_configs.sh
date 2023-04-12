#!/bin/sh

# Adjusts the configuration options to build the variants correctly

test -n "$RHTEST" && exit 0

DEBUGBUILDSENABLED=$1
if [ -z "$DEBUGBUILDSENABLED" ]; then
	exit 1
fi

if [ -z "$FLAVOR" ]; then
	FLAVOR=rhel
fi

if [ "$FLAVOR" = "fedora" ]; then
	SECONDARY=rhel
else
	SECONDARY=fedora
fi

for i in kernel-*-"$FLAVOR".config; do
	NEW=kernel-"$SPECVERSION"-$(echo "$i" | cut -d - -f2- | sed s/-"$FLAVOR"//)
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
