#!/bin/sh

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

for f in `find conduit/ -type f \( -name "*.py" \)`
do
    pyflakes $f
done
