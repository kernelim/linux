##
# check-multiple-entries.awk - simple AWK program to scan info/owners.yaml
# 			       for subsystems defined more than one time,
#			       and stop the build process in such cases.
#
#  Copyright (c) 2021 Red Hat, Inc.
#

BEGIN {
    FS = ":";
} /subsystem:/ {
    s[$2] += 1;
} END {
    for (i in s) {
        if (s[i] > 1) {
            printf("ERROR: %s: %d entries found for %s\n",
                   ARGV[1], s[i], i);
            exit 1;
        }
    }
}
