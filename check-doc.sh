#!/bin/bash
PYTHONPATH=/home/john/Programming/src/epydoc/src/ \
epydoc	-o doc --name conduit --css white \
		--url http://john.greenbirdsystems.com \
		--inheritance listed \
		--no-frames \
		--show-private \
		--parse-only \
		--graph all \
		--verbose \
		--check \
		conduit
