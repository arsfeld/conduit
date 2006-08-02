#!/bin/bash
PYTHONPATH=/home/john/Programming/src/epydoc/src/ \
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
