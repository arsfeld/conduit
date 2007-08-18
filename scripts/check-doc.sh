#!/bin/bash

APP="conduit/start_conduit.py"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

epydoc  -o doc --name conduit --css white \
        --url http://www.conduit-project.org \
        --inheritance listed \
        --no-frames \
        --show-private \
        --parse-only \
        --graph all \
        --verbose \
        --check \
        conduit \
        conduit/dataproviders
