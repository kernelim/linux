#!/bin/bash
#
# this script is a helper script for i686 and x86_64 builds.  It gets the
# random number generator running.

echo -n "Trying hardware random number generator ..."
if ! rngd -r /dev/hwrandom >& /dev/null; then
	echo "failed"
	# try the pseudo-random number generator
	echo "Using pseudo-random number instead"
	rngd -r /dev/urandom >& /dev/null
else
	echo "succeeded"
fi
