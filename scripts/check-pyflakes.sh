#!/bin/sh

for f in `find ../conduit/ -type f \( -name "*.py" \)`
do
    pyflakes $f
done
