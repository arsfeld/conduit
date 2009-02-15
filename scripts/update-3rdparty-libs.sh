#!/bin/sh

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

#update flickrapi
echo "Not updating flickrapi (use stable releases only)"

#update pyfacebook
echo "Updating pyfacebook"
svn export --force http://pyfacebook.googlecode.com/svn/trunk/facebook/__init__.py conduit/modules/FacebookModule/pyfacebook/__init__.py

#update pybackpack
echo "Updating pybackpack"
for i in COPYING backpack.py; do
    echo "    ...downloading $i"
    wget -qO conduit/modules/BackpackModule/backpack/${i} http://github.com/dustin/py-backpack/tree/master%2F${i}?raw=true
done

#update pyrtm
echo "Updating pyrtm"
wget -qO conduit/modules/UNSUPPORTED/RTMModule/rtm.py "http://repo.or.cz/w/pyrtm.git?a=blob_plain;f=rtm.py;hb=HEAD

