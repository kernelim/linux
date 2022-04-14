#!/bin/bash
#
# This script takes the merged config files and processes them through oldconfig
# and listnewconfig
#
# Globally disable suggestion of appending '|| exit' or '|| return' to cd/pushd/popd commands
# shellcheck disable=SC2164

usage()
{
	# alphabetical order please
	echo "process_configs.sh [ options ] package_name kernel_version"
	echo "     -a: report all errors, equivalent to [-c -n -w -i]"
	echo "     -c: error on mismatched config options"
	echo "     -i: continue on error"
	echo "     -n: error on unset config options"
	echo "     -t: test run, do not overwrite original config"
	echo "     -w: error on misconfigured config options"
	echo "     -z: commit new configs to pending directory"
	echo ""
	echo "     A special CONFIG file tag, process_configs_known_broken can be added as a"
	echo "     comment to any CONFIG file.  This tag indicates that there is no way to "
	echo "     fix a CONFIG's entry.  This tag should only be used in extreme cases"
	echo "     and is not to be used as a workaround to solve CONFIG problems."
	exit 1
}

die()
{
	echo "$1"
	exit 1
}

get_cross_compile()
{
	arch=$1
	if [[ "$CC_IS_CLANG" -eq 1 ]]; then
		echo "$arch"
	else
		echo "scripts/dummy-tools/"
	fi
}

# stupid function to find top of tree to do kernel make configs
switch_to_toplevel()
{
	path="$(pwd)"
	while test -n "$path"
	do
		test -e "$path"/MAINTAINERS && \
			test -d "$path"/drivers && \
			break

		path=$(dirname "$path")
	done

	test -n "$path"  || die "Can't find toplevel"
	echo "$path"
}

checkoptions()
{
	/usr/bin/awk '

		/is not set/ {
			split ($0, a, "#");
			split(a[2], b);
			if (NR==FNR) {
				configs[b[1]]="is not set";
			} else {
				if (configs[b[1]] != "" && configs[b[1]] != "is not set")
					 print "Found # "b[1] " is not set, after generation, had " b[1] " " configs[b[1]] " in Source tree";
			}
		}

		/=/     {
			split ($0, a, "=");
			if (NR==FNR) {
				configs[a[1]]=a[2];
			} else {
				if (configs[a[1]] != "" && configs[a[1]] != a[2])
					 print "Found "a[1]"="a[2]" after generation, had " a[1]"="configs[a[1]]" in Source tree";
			}
		}
	' "$1" "$2" > .mismatches

	checkoptions_error=false
	if test -s .mismatches
	then
		while read -r LINE
		do
			if find ./ -name "$(echo "$LINE" | awk -F "=" ' { print $1 } ' | awk ' { print $2 }')" -print0 | xargs -0 grep ^ | grep -q "process_configs_known_broken"; then
				# This is a known broken config.
				# See script help warning.
				checkoptions_error=false
			else
				checkoptions_error=true
				break
			fi
		done < .mismatches

		! $checkoptions_error && return

		echo "Error: Mismatches found in configuration files"
		cat .mismatches
		RETURNCODE=1
		[ "$CONTINUEONERROR" ] || exit 1
	fi
}

parsenewconfigs()
{
	tmpdir=$(mktemp -d)

	# This awk script reads the output of make listnewconfig
	# and puts it into CONFIG_FOO files. Using the output of
	# listnewconfig is much easier to ensure we get the default
	# output.
        /usr/bin/awk -v BASE="$tmpdir" '
                /is not set/ {
                        split ($0, a, "#");
                        split(a[2], b);
                        OUT_FILE=BASE"/"b[1];
                        print $0 >> OUT_FILE;
                }

                /=/     {
                        split ($0, a, "=");
                        OUT_FILE=BASE"/"a[1];
                        if (a[2] == "n")
                                print "# " a[1] " is not set" >> OUT_FILE;
                        else
                                print $0 >> OUT_FILE;
                }

        ' .newoptions

	# This awk script parses the output of helpnewconfig.
	# Each option is separated between ----- markers
	# The goal is to put all the help text as a comment in
	# each CONFIG_FOO file. Because of how awk works
	# there's a lot of moving files around and catting to
	# get what we need.
        /usr/bin/awk -v BASE="$tmpdir" '
                BEGIN { inpatch=0;
			outfile="none";
                        symbol="none"; }
                /^Symbol: .*$/ {
                        split($0, a, " ");
                        symbol="CONFIG_"a[2];
                        outfile=BASE "/fake_"symbol
                }
                /-----/ {
			if (inpatch == 0) {
				inpatch = 1;
			}
                        else {
                                if (symbol != "none") {
                                    system("cat " outfile " " BASE "/" symbol " > " BASE "/tmpf");
                                    system("mv " BASE "/tmpf " BASE "/" symbol);
                                    symbol="none"
				}
                                outfile="none"
				inpatch = 0;
                        }
                }
                !/-----/ {
                        if (inpatch == 1 && outfile != "none") {
                                print "# "$0 >> outfile;
                        }
                }


        ' .helpnewconfig

	pushd "$tmpdir" &> /dev/null
	rm fake_*
	popd &> /dev/null
	for f in "$tmpdir"/*; do
		[[ -e "$f" ]] || break
		cp "$f" "$SCRIPT_DIR/pending$FLAVOR/generic/"
	done

	rm -rf "$tmpdir"
}

function commit_new_configs()
{
	# assume we are in $source_tree/configs, need to get to top level
	pushd "$(switch_to_toplevel)" &>/dev/null

	for cfg in "$SCRIPT_DIR/${PACKAGE_NAME}${KVERREL}${SUBARCH}"*.config
	do
		arch=$(head -1 "$cfg" | cut -b 3-)
		cfgtmp="${cfg}.tmp"
		cfgorig="${cfg}.orig"
		cat "$cfg" > "$cfgorig"

		if [ "$arch" = "EMPTY" ]
		then
			# This arch is intentionally left blank
			continue
		fi
		echo -n "Checking for new configs in $cfg ... "

		make ${MAKEOPTS} ARCH="$arch" CROSS_COMPILE=$(get_cross_compile $arch) KCONFIG_CONFIG="$cfgorig" listnewconfig >& .listnewconfig
		grep -E 'CONFIG_' .listnewconfig > .newoptions
		if test -s .newoptions
		then
			make ${MAKEOPTS} ARCH="$arch" CROSS_COMPILE=$(get_cross_compile $arch) KCONFIG_CONFIG="$cfgorig" helpnewconfig >& .helpnewconfig
			parsenewconfigs
		fi
		rm .newoptions
		echo "done"
	done

	git add "$SCRIPT_DIR/pending$FLAVOR"
	git commit -m "[redhat] AUTOMATIC: New configs"
}

function process_configs()
{
	# assume we are in $source_tree/configs, need to get to top level
	pushd "$(switch_to_toplevel)" &>/dev/null

	for cfg in "$SCRIPT_DIR/${PACKAGE_NAME}${KVERREL}${SUBARCH}"*.config
	do
		arch=$(head -1 "$cfg" | cut -b 3-)
		cfgtmp="${cfg}.tmp"
		cfgorig="${cfg}.orig"
		cat "$cfg" > "$cfgorig"

		if [ "$arch" = "EMPTY" ]
		then
			# This arch is intentionally left blank
			continue
		fi
		echo -n "Processing $cfg ... "

		make ${MAKEOPTS} ARCH="$arch" CROSS_COMPILE=$(get_cross_compile $arch) KCONFIG_CONFIG="$cfgorig" listnewconfig >& .listnewconfig
		grep -E 'CONFIG_' .listnewconfig > .newoptions
		if test -n "$NEWOPTIONS" && test -s .newoptions
		then
			echo "Found unset config items, please set them to an appropriate value"
			cat .newoptions
			rm .newoptions
			RETURNCODE=1
			[ "$CONTINUEONERROR" ] || exit 1
		fi
		rm .newoptions

		grep -E 'config.*warning' .listnewconfig > .warnings
		if test -n "$CHECKWARNINGS" && test -s .warnings
		then
			echo "Found misconfigured config items, please set them to an appropriate value"
			cat .warnings
			rm .warnings
			RETURNCODE=1
			[ "$CONTINUEONERROR" ] || exit 1
		fi
		rm .warnings

		rm .listnewconfig

		make ${MAKEOPTS} ARCH="$arch" CROSS_COMPILE=$(get_cross_compile $arch) KCONFIG_CONFIG="$cfgorig" olddefconfig > /dev/null || exit 1
		echo "# $arch" > "$cfgtmp"
		cat "$cfgorig" >> "$cfgtmp"
		if test -n "$CHECKOPTIONS"
		then
			checkoptions "$cfg" "$cfgtmp"
		fi
		# if test run, don't overwrite original
		if test -n "$TESTRUN"
		then
			rm -f "$cfgtmp"
		else
			mv "$cfgtmp" "$cfg"
		fi
		rm -f "$cfgorig"
		echo "done"
	done
	rm "$SCRIPT_DIR"/*.config*.old
	popd > /dev/null

	echo "Processed config files are in $SCRIPT_DIR"
}

CHECKOPTIONS=""
CONTINUEONERROR=""
NEWOPTIONS=""
TESTRUN=""
CHECKWARNINGS=""
MAKEOPTS=""
CC_IS_CLANG=0

RETURNCODE=0

while [[ $# -gt 0 ]]
do
	key="$1"
	case $key in
		-a)
			CHECKOPTIONS="x"
			CONTINUEONERROR="x"
			NEWOPTIONS="x"
			CHECKWARNINGS="x"
			;;
		-c)
			CHECKOPTIONS="x"
			;;
		-h)
			usage
			;;
		-i)
			CONTINUEONERROR="x"
			;;
		-n)
			NEWOPTIONS="x"
			;;
		-t)
			TESTRUN="x"
			;;
		-w)
			CHECKWARNINGS="x"
			;;
		-z)
			COMMITNEWCONFIGS="x"
			;;
		-m)
			shift
			if [ "$1" = "CC=clang" -o "$1" = "LLVM=1" ]; then
				CC_IS_CLANG=1
			fi
			MAKEOPTS="$MAKEOPTS $1"
			;;
		*)
			break;;
	esac
	shift
done

PACKAGE_NAME="${1:-kernel}" # defines the package name used
KVERREL="$(test -n "$2" && echo "-$2" || echo "")"
SUBARCH="$(test -n "$3" && echo "-$3" || echo "")"
FLAVOR="$(test -n "$4" && echo "-$4" || echo "-common")"
SCRIPT=$(readlink -f "$0")
SCRIPT_DIR=$(dirname "$SCRIPT")

# Most RHEL options are options we want in Fedora so RHEL pending settings head
# to common/
if [ "$FLAVOR" = "-rhel" ]
then
	FLAVOR="-common"
fi

# to handle this script being a symlink
cd "$SCRIPT_DIR"

if test -n "$COMMITNEWCONFIGS"; then
	commit_new_configs
else
	process_configs
fi

exit $RETURNCODE
