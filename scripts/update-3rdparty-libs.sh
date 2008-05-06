#!/bin/sh

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

#update flickrapi
echo "Please use stable flickr api releases"

#update pyfacebook
svn export --force http://pyfacebook.googlecode.com/svn/trunk/facebook/__init__.py conduit/modules/FacebookModule/pyfacebook/__init__.py

#update pybackpack
#for i in COPYING backpack.py; do
#    wget -qO conduit/modules/BackpackModule/backpack/${i} http://github.com/dustin/py-backpack/tree/master%2F${i}?raw=true
#done



