#!/bin/sh
APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

./scripts/maintainer.py \
    --revision=0.3.9 \
    --package-name=Conduit \
    --package-version=0.3.10 \
    --package-module=conduit \
    --release-note-template=scripts/release-template.txt \
    $*
