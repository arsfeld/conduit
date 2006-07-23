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

IS_LOCAL = False

name = os.path.join(os.path.dirname(__file__), '..')
print name
if os.path.exists(name) and os.path.isdir(name) and os.path.isfile(name+"/conduit/ChangeLog") :
    print "Running uninstalled Conduit"
    IS_LOCAL = True
else:
    print "Running installed version of Conduit."

# Now set up conduit to run non-installed
if IS_LOCAL:
    print "Modifying python path"
    sys.path.insert(0, os.path.abspath(name))
    import conduit
    print "Modifying SHARED_DATA_DIR"
    conduit.SHARED_DATA_DIR =  os.path.join(os.path.abspath(name),"conduit","data")
    print "Modifying GLADE_FILE"
    conduit.GLADE_FILE =  os.path.join(os.path.abspath(name),"conduit","data","conduit.glade")
    print "Modifying SHARED_MODULE_DIR"
    conduit.SHARED_MODULE_DIR =  os.path.join(os.path.abspath(name),"conduit")

#Dir where 3rd party libraries live if shipped with conduit
conduit.EXTRA_LIB_DIR = os.path.join(os.path.abspath(name),"contrib")

# Remove all the tools we loaded
del sys, os

# Start the application
import conduit.MainWindow as MainWindow
test = MainWindow()
test.__main__()
 
