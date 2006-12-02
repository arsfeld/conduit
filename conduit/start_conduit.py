#!/usr/bin/python
"""
This module tests whether conduit appears 
to be running from the source directory.

If this is the case it will modify the conduit
constants such as SHARED_DATA_DIR to reflect this
environment.

Copyright: John Stowers, 2006
License: GPLv2
"""

#
# Stuff that allows us to import uninstalled conduit module
# This code is modified from deskbar-applet
#

import sys
import os
import os.path

# Check if the given path looks like the conduit parent path
# Add the parent dir of conduit to the python path if so
name = os.path.join(os.path.dirname(__file__), '..')
if os.path.exists(name) and os.path.isdir(name) and os.path.isfile(os.path.join(name,"conduit","ChangeLog")):
    sys.path.insert(0, os.path.abspath(name))
    import conduit
    conduit.IS_INSTALLED = False
    conduit.SHARED_DATA_DIR =  os.path.join(os.path.abspath(name),"conduit","data")
    conduit.GLADE_FILE =  os.path.join(os.path.abspath(name),"conduit","data","conduit.glade")
    conduit.SHARED_MODULE_DIR =  os.path.join(os.path.abspath(name),"conduit")
    conduit.EXTRA_LIB_DIR = os.path.join(os.path.abspath(name),"contrib")
else:
    import conduit
    conduit.IS_INSTALLED = True
    #FIXME: Autotools these paths.....
    conduit.SHARED_DATA_DIR =  "/usr/share/conduit/data"
    conduit.GLADE_FILE =  "/usr/share/conduit/data/conduit.glade"
    conduit.SHARED_MODULE_DIR =  "/usr/share/conduit"
    conduit.EXTRA_LIB_DIR = "/usr/share/conduit/contrib"

conduit.log("Conduit Installed: %s" % conduit.IS_INSTALLED)
conduit.log("Log Level: %s" % conduit.LOG_LEVEL)

# Start the application
from conduit.MainWindow import conduit_main
conduit_main()
 
