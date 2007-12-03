#!/bin/sh

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

#update flickrapi
svn export --force https://flickrapi.svn.sourceforge.net/svnroot/flickrapi/trunk/flickrapi/ conduit/modules/FlickrModule/flickrapi/

#update pyfacebook
svn export --force http://pyfacebook.googlecode.com/svn/trunk/facebook/__init__.py conduit/modules/FacebookModule/pyfacebook/__init__.py

