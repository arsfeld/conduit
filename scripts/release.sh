#!/bin/sh
APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

#FIXME: Add version number command
./scripts/maintainer.py \
    --debug \
    --revision=0.3.6 \
    --package-name=Conduit \
    --package-version=0.3.7 \
    --package-module=conduit \
    --release-note-template=scripts/release-template.txt \
    --create-release-note
