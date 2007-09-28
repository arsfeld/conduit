#!/bin/bash

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

epydoc  -o doc --name conduit --css white \
        --url http://www.conduit-project.org \
        --inheritance listed \
        --no-frames \
        --parse-only \
        --graph all \
        --verbose \
        conduit \
        conduit/dataproviders \
        conduit/datatypes \
        doc/ExampleModule.py
