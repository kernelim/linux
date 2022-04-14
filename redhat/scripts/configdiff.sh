#! /bin/bash

RHCP=redhat/configs
RHCP_RHEL=$RHCP
WORK=.work
PACKAGE_NAME='kernel' # should come from Makefile.common

die()
{
    echo "$1"
    exit 1
}

get_configarch()
{
    # given a filename provide the <arch> for $RHCP_RHEL/pending-common/generic/
    # the supported arch is embedded in the filename, translate that
    # to the srcarch used in the $RHCP_RHEL/pending-common/generic path.
    file=$1

    # make dist-configs-prep uses <package-name>-<arch>-<variant>.config
    # the trick is to get the <package-name> and filter it out
    arch="${file/$PACKAGE_NAME-/}"
    arch="${arch/-*/}"

    # translate arch
    case $arch in
        x86_64 )	echo "x86/x86_64" ;;
        ppc64le )	echo "powerpc" ;;
        s390x )		echo "s390x" ;;
        aarch64 )	echo "arm/aarch64" ;;
        *)		die "Unsupported arch $arch" ;;
    esac
}

find_conflicts()
{
    # create master array, duplicate entries should have matching values
    # if they don't, we can't create a 'pending-common/generic/' entry.  We will have to
    # resort to a 'pending-common/generic/<arch>' entry instead.  Print config options that
    # have conflicting defaults.
  /usr/bin/awk '

    /is not set/ {
                split($0, a, "#");
                split(a[2], b);
                if (configs[b[1]] == "") {
            configs[b[1]]="is not set";
        } else {
            if (configs[b[1]] != "is not set")
                print "configs[b[1]]"
        }
    }

    /=/ {
                split($0, a, "=");
                if (configs[a[1]] == "") {
            configs[a[1]]=a[2];
        } else {
            if (configs[a[1]] != a[2])
                print "configs[a[1]]"
        }
    }
    # punt all arch specific stuff to the <arch> directory
    /CONFIG_X86/ || /CONFIG_PPC/ || /CONFIG_ARM/ || /CONFIG_S390/

  ' $WORK/kernel*.config
}

save_defaults()
{
    conflicts=$1

    echo "Saving config defaults"

    # write shared config values to $RHCP_RHEL/pending-common/generic
    # combine all configs and filter out conflicts, then unique sort them
    # this avoids the duplicate configs from each kernel*.config file.
    # With conflicts filtered out, all files should be new.
    cat $WORK/kernel*.config | grep -v -f "$conflicts" | sort -u > $WORK/.configs
    while read -r config
    do
        file="$(echo "$config" | cut -f1 -d '=')"
        path="$RHCP_RHEL/pending-common/generic/$file"

        # translate the =n to 'is not set'
        if [[ "$config" = *"=n" ]]
        then
            value="# $file is not set"
        else
            value="$config"
        fi

        # normal path
        test ! -e "$path" && echo "$value" > "$path" && continue

        # Existing files should come from newly invalid config values
        # if so, let's find and overwrite all instances of it
        paths="$(find $RHCP_RHEL -name "$file")"
        for path in $paths
        do
            # special case, anything not set, don't overwrite, keep disabled.
            # a disabled config option is never invalid
            grep -q 'is not set' "$path" && continue

            echo "$value" > "$path"
        done

    done < $WORK/.configs

    # write conflicting config values to $RHCP_RHEL/pending-common/generic/arch
    for f in "$WORK"/kernel*.config
    do
        grep -f "$conflicts" "$f" > $WORK/.configs
        test ! -s $WORK/.configs && continue
        arch="$(get_configarch "$(basename "$f")")" || die "$arch"

        while read -r config
        do
            file="$(echo "$config" | cut -f1 -d '=')"
            path="$RHCP_RHEL/pending-common/generic/$arch/$file"

            # translate the =n to 'is not set'
            if [[ "$config" = *"=n" ]]
            then
                value="# $file is not set"
            else
                value="$config"
            fi

            echo "$value" > "$path"
        done < $WORK/.configs
    done
}

generate_rh_config()
{
    echo "Generating rh_config diffs"
    rm -rf $WORK
    mkdir $WORK

    # generate the new config options
    # invalid config values are handle inherently here because the kconf tool
    # spits them out as new configs
    for f in "$RHCP"/kernel*.config
    do
	echo "Working on $f"

        cp "$f" .config
	config="$(basename "$f")"
        arch="$(head -1 "$f" | cut -b 3-)" || die "$arch"

        make ARCH="$arch" listnewconfig 2>/dev/null | grep -E 'CONFIG_' | cut -d'#' -f1 > $WORK/"$config"
    done

    # check for conflicting default config values
    find_conflicts > $WORK/.conflicts
    save_defaults "$WORK/.conflicts"

    rm -rf $WORK
}

make dist-configs-prep > /dev/null || die "Failed make dist-prep"
generate_rh_config
