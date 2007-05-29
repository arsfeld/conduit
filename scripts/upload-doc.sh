#!/bin/bash
rsync -Ptz doc/*.{html,gif,png,py,js,css} root@greenbirdsystems.com:/var/www/conduit-project.org/doc/conduit
