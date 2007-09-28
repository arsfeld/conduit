#!/bin/bash

APP="conduit/conduit"
if [ ! -f $APP ] ; then
    echo "ERROR: Must be run from top directory"
    exit 1
fi

rsync -Ptz doc/*.{html,gif,png,py,js,css} root@greenbirdsystems.com:/var/www/conduit-project.org/doc/conduit
