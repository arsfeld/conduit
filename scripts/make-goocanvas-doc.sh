#!/bin/bash
PYTHONPATH=/home/john/Programming/src/epydoc/src/ \
epydoc 	-o goocanvas-doc --css white \
		--inheritance listed \
		--show-private \
		--graph all \
		--verbose \
		goocanvas
