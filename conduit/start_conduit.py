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
    print "Running uninstalled Conduit"
    print "Modifying python path"
    sys.path.insert(0, os.path.abspath(name))
    import conduit
    conduit.IS_INSTALLED = False
    print "Modifying SHARED_DATA_DIR"
    conduit.SHARED_DATA_DIR =  os.path.join(os.path.abspath(name),"conduit","data")
    print "Modifying GLADE_FILE"
    conduit.GLADE_FILE =  os.path.join(os.path.abspath(name),"conduit","data","conduit.glade")
    print "Modifying SHARED_MODULE_DIR"
    conduit.SHARED_MODULE_DIR =  os.path.join(os.path.abspath(name),"conduit")
    print "Modifying EXTRA_LIB_DIR"
    conduit.EXTRA_LIB_DIR = os.path.join(os.path.abspath(name),"contrib")
else:
    print "Running installed version of Conduit."
    import conduit
    conduit.IS_INSTALLED = True
    #FIXME: Autotools these paths.....
    print "Modifying SHARED_DATA_DIR"
    conduit.SHARED_DATA_DIR =  "/usr/share/conduit/data"
    print "Modifying GLADE_FILE"
    conduit.GLADE_FILE =  "/usr/share/conduit/data/conduit.glade"
    print "Modifying SHARED_MODULE_DIR"
    conduit.SHARED_MODULE_DIR =  "/usr/share/conduit"
    print "Modifying EXTRA_LIB_DIR"
    conduit.EXTRA_LIB_DIR = "/usr/share/conduit/contrib"
    
# Start the application
import conduit.MainWindow as MainWindow
test = MainWindow()
test.__main__()
 
