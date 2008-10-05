#!/bin/bash

if [ ! -f "conduit/conduit" ] ; then
    echo "ERROR: Must be run from top directory\n$USAGE"
    exit 1
fi

cd po &>/dev/null
POS=`ls *.po`
cd - &>/dev/null

for p in $POS
do
    out=po/`echo $p | sed -e 's/\.po//'`/LC_MESSAGES
    mkdir -p $out
    msgfmt --output-file=$out/conduit.mo po/$p 
done


