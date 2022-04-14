#!/bin/bash
#
# Update the changelog in the current branch to match the changelog in
# ark-latest.  CI runs this against the os-build branch so the change log
# entries from the new release are pulled in and used to figure out what's
# changed in the *next* release.

set -x
set -e

git checkout ark-latest -- redhat/kernel.changelog-8.99
git add redhat/kernel.changelog-8.99
git checkout ark-latest -- redhat/marker
git add redhat/marker

# Did anything change?
LINES_CHANGED=$(git diff --cached | wc -l)
if [ "${LINES_CHANGED}" != "0" ]; then
    git commit -m "Updated changelog for the release based on $(cat redhat/marker)"
fi
