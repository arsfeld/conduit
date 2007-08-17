#!/bin/bash
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
