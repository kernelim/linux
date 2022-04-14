#!/bin/bash

arg=$1
shift
case $arg in
    describe )
        if [ -n "$EGIT_OVERRIDE_DESCRIBE" ]
        then
            # Should be a version, e.g. v5.9-rc8 or v5.9-rc7-1449-g57b6fb86b0ac
            echo "$EGIT_OVERRIDE_DESCRIBE"
        else
            git describe "$@"
        fi
        ;;
    * )
        git "$arg" "$@"
        ;;
esac
