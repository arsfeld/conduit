"""
This module tests whether Barracuda appears 
to be running from the source directory.

If this is the case it will modify the barracuda
constants such as SHARED_DATA_DIR to reflect this
environment.
"""

#
# Stuff that allows us to import uninstalled barracuda module
# This code is modified from deskbar-applet
#

import sys
from os.path import join, dirname, abspath, isdir, isfile, exists

# Check if the given path looks like the barracuda parent path
# Add the parent dir of barracuda to the python path if so

IS_LOCAL = False

name = join(dirname(__file__), '..')
print abspath(name)
if exists(name) and isdir(name) and isfile(name+"/conduit/ChangeLog") :
	print 'Running uninstalled Conduit, modifying python path'
	sys.path.insert(0, abspath(name))
	IS_LOCAL = True
else:
	print "Running installed version of Conduit."


#
# Now set up Barracuda to run non-installed
#

if IS_LOCAL:
	import conduit
	conduit.SHARED_DATA_DIR = abspath(name) + "/conduit/data"

#
# Remove all the tools we loaded
#
del sys, join, dirname, abspath, isdir, isfile, exists


import conduit.MainWindow as MainWindow
import conduit.TypeConverter as TypeConverter

test = MainWindow("Conduit Test Application")
test.__main__()
 
