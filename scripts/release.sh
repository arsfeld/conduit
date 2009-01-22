#!/bin/sh
APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

./scripts/maintainer.py \
    --revision=0.3.15 \
    --package-name=Conduit \
    --package-version=0.3.16 \
    --package-module=conduit \
    --release-note-template=scripts/release-template.txt \
    $*
