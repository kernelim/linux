#!/bin/bash
if [ -s "$REDHAT/linux-kernel-test.patch" ]; then
	echo "linux-kernel-test.patch is not empty, aborting" >&2;
	exit 1;
fi

RELEASE=$(sed -n -e 's/^RHEL_RELEASE\ =\ \(.*\)/\1/p' "$REDHAT"/../Makefile.rhelver)

YVER=$(echo "$RELEASE" | cut -d "." -f 1)
YVER=${YVER:="$RELEASE"}
ZMAJ=$(echo "$RELEASE" | cut -s -d "." -f 2)
ZMAJ=${ZMAJ:=0}
ZMIN=$(echo "$RELEASE" | cut -s -d "." -f 3)
ZMIN=${ZMIN:=0}

if [ "$BUMP_RELEASE" == "no" ]; then
	NEW_RELEASE="$RELEASE";
elif [ "$ZSTREAM_FLAG" == "no" ]; then
	if [ "$YSTREAM_FLAG" == "yes" ]; then
		NEW_RELEASE="$((RELEASE + 1))";
	else
		EARLY_YBUILD=$(sed -n -e 's/^EARLY_YBUILD:=\(.*\)/\1/p' "$REDHAT"/../Makefile.rhelver);
		EARLY_YRELEASE=$(sed -n -e 's/^EARLY_YRELEASE:=\(.*\)/\1/p' "$REDHAT"/../Makefile.rhelver);
		if [ "$EARLY_YBUILD" != "$RELEASE" ]; then
			NEW_EARLY_YRELEASE=1;
		else
			NEW_EARLY_YRELEASE="$((EARLY_YRELEASE + 1))";
		fi
		sed -i -e "s/^EARLY_YBUILD:=$EARLY_YBUILD/EARLY_YBUILD:=$RELEASE/" "$REDHAT"/../Makefile.rhelver;
		sed -i -e "s/^EARLY_YRELEASE:=$EARLY_YRELEASE/EARLY_YRELEASE:=$NEW_EARLY_YRELEASE/" "$REDHAT"/../Makefile.rhelver;
		NEW_RELEASE=$RELEASE;
	fi
elif [ "$ZSTREAM_FLAG" == "yes" ]; then
	NEW_RELEASE=$YVER.$((ZMAJ+1)).1;
elif [ "$ZSTREAM_FLAG" == "branch" ]; then
	NEW_RELEASE=$YVER.$ZMAJ.$((ZMIN+1));
else
	echo "$(basename "$0") invalid <zstream> value, allowed [no|yes|branch]" >&2;
	exit 1;
fi

sed -i -e "s/RHEL_RELEASE\ =.*/RHEL_RELEASE\ =\ $NEW_RELEASE/" "$REDHAT"/../Makefile.rhelver;

