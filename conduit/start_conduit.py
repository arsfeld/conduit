"""
This module tests whether conduit appears 
to be running from the source directory.

If this is the case it will modify the conduit
constants such as SHARED_DATA_DIR to reflect this
environment.
"""

#
# Stuff that allows us to import uninstalled conduit module
# This code is modified from deskbar-applet
#

import sys
from os.path import join, dirname, abspath, isdir, isfile, exists

# Check if the given path looks like the conduit parent path
# Add the parent dir of conduit to the python path if so

IS_LOCAL = False

name = join(dirname(__file__), '..')
print abspath(name)
if exists(name) and isdir(name) and isfile(name+"/conduit/ChangeLog") :
    print "Running uninstalled Conduit"
    IS_LOCAL = True
else:
    print "Running installed version of Conduit."

# Now set up conduit to run non-installed
if IS_LOCAL:
    print "Modifying python path"
    sys.path.insert(0, abspath(name))
    import conduit
    print "Modifying SHARED_DATA_DIR"
    conduit.SHARED_DATA_DIR = abspath(name) + "/conduit/data"
    print "Modifying GLADE_FILE"
    conduit.GLADE_FILE = abspath(name) + "/conduit/data/conduit.glade"
    print "Modifying SHARED_MODULE_DIR"
    conduit.SHARED_MODULE_DIR = abspath(name) + "/conduit"

#
# Remove all the tools we loaded
#
del sys, join, dirname, abspath, isdir, isfile, exists


import conduit.MainWindow as MainWindow

test = MainWindow()
test.__main__()
 
