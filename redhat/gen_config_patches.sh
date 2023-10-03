#!/bin/bash
#
# Creates commits that moves all configuration options for a subsystem from the
# pending configuration directory to the common configuration directory. Each
# commit is contained on a branch named "configs/<date>/<subsystem path>.
#
# The commit message is formed from redhat/commit_template and includes Cc
# information for the relevant maintainers using get_maintainers.pl. This
# requires that you have $RHMAINTAINERS pointing to a valid maintainer file.

if ! git show -s --oneline HEAD | grep -q "AUTOMATIC: New configs"; then
	echo "The git HEAD doesn't look like the correct commit"
	exit 1
fi

config_bundles_dir=$(mktemp -d)
tmpdir=$(mktemp -d)

function cleanup {
	rm -rf "$config_bundles_dir"
	rm -rf "$tmpdir"
}
trap cleanup EXIT

# Easy way to get each of the files to process
# Not interested in Fedora configs
git diff --name-only HEAD HEAD^ | grep -v "pending-fedora" > "$tmpdir"/new_config_files

if [ ! -s "$tmpdir"/new_config_files ]; then
	echo "No config changes after filtering"
	exit 0
fi

while read -r line; do
	# Read all the files and split up by file path of each config item.
	# ethernet and net get handled separately others can be added as needed
	#
	# A sample of the input file we're parsing is:
	# # CONFIG_ARCH_RANDOM:
	# #
	# # Random number generation (part of the ARMv8.5 Extensions)
	# # provides a high bandwidth, cryptographically secure
	# # hardware random number generator.
	# #
	# # Symbol: ARCH_RANDOM [=y]
	# # Type  : bool
	# # Prompt: Enable support for random number generation
	# #   Location:
	# #	 -> Kernel Features
	# #	   -> ARMv8.5 architectural features
	# #   Defined at arch/arm64/Kconfig:1533
	# #
	# CONFIG_ARCH_RANDOM=y
	awk -v BASE="$config_bundles_dir" '
	function strip_kconfig_path(path_with_text)
	{
		sub("#.*Defined at ", "", path_with_text)
		sub(":[0-9]+", "", path_with_text)
		return path_with_text
	}
	/Defined at drivers\/net\/ethernet/ {
		# For configs in here, bundle configs by vendor
		kconfig_path=strip_kconfig_path($0);
		split(kconfig_path, path_parts, "/")
		# Only use the first component after drivers/net/ethernet
		subsystem_path=BASE"/drivers:net:ethernet:"path_parts[4]
		print config >> subsystem_path;
		next;
	}
	/Defined at drivers\/net/ {
		# For configs in here, bundle configs by driver type
		kconfig_path=strip_kconfig_path($0);
		split(kconfig_path, path_parts, "/")
		subsystem_path=BASE"/drivers:net:"path_parts[3];
		print config >> subsystem_path;
		next;
	}
	/Defined at / {
		# Bundle all other configuration by the first two components of the path
		kconfig_path=strip_kconfig_path($0);
		split(kconfig_path, path_parts, "/")
		subsystem_path=BASE"/"path_parts[1]":"path_parts[2]
		print config >> subsystem_path;
		next;
	}
	/^# Symbol: .*/ {
		split($0, a, " ");
		config="CONFIG_"a[3];
		#print config;
	}
	' "$line"
done < "$tmpdir"/new_config_files

# $config_bundles_dir now contains files containing a list of configs per file path
for f in "$config_bundles_dir"/*; do
	if [ ! -e "$f" ]; then
		echo "Missing generated config file: $f"
		exit 1  # No files in config_bundles_dir, abort
	fi
	# we had to change to : for the file name so switch it back
	_f=$(basename "$f" | sed -e 's/:/\//g')
	# Commit subject
	echo "[redhat] New configs in $_f" > "$tmpdir"/commit
	echo "" >> "$tmpdir"/commit
	# And the boiler plate
	cat redhat/commit_template >> "$tmpdir"/commit
	# This loop actually grabs the help text to put in the commit
	while read -r line; do
		# last line is the actual config we need to put in the dir
		tail -n 1 redhat/configs/pending-rhel/generic/"$line" > redhat/configs/rhel/generic/"$line"
		# get everything except the last line for the commit text
		head -n -1 redhat/configs/pending-rhel/generic/"$line" | sed -e 's/^#//g' >> "$tmpdir"/commit
		# add a nice separator that renders in gitlab
		echo -ne "\n---\n\n" >> "$tmpdir"/commit
		# remove the pending option
		rm redhat/configs/pending-rhel/generic/"$line"
	done < "$f"
	if [ -n "$RHMAINTAINERS" ] && [ -f ./scripts/get_maintainer.pl ] && [ -f "$RHMAINTAINERS" ]; then
		echo "" >> "$tmpdir"/commit
		./scripts/get_maintainer.pl --no-rolestats --mpath "$RHMAINTAINERS" --no-git --no-git-fallback -f "$_f"  | sed "s/^/Cc: /" >> "$tmpdir"/commit
	fi
	# We do a separate branch per config commit
	if ! git checkout -b "configs/$(date +%F)/$_f"; then
		printf "Unable to check out configs/%s/%s branch!\n" "$(date +%F)" "$_f"
		exit 1
	fi
	# One file path is done, time to commit!
	git add redhat/configs
	git commit -s -F "$tmpdir"/commit
	git checkout os-build
done
