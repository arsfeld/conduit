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
import os, os.path

# Look for ChangeLog to see if we are installed
directory = os.path.join(os.path.dirname(__file__), '..')
changelog = os.path.join(directory,"ChangeLog")
if os.path.exists(changelog):
    sys.path.insert(0, os.path.abspath(directory))
    import conduit
else:
    #Support alternate install paths   
    if not '@PYTHONDIR@' in sys.path:
        sys.path.insert(0, '@PYTHONDIR@')
    import conduit
    conduit.IS_INSTALLED =          True
    conduit.APPVERSION =            '@VERSION@'
    conduit.SHARED_DATA_DIR =       os.path.abspath('@PKGDATADIR@')
    conduit.GLADE_FILE =            os.path.join(conduit.SHARED_DATA_DIR, "conduit.glade")
    conduit.SHARED_MODULE_DIR =     os.path.abspath('@PKGLIBDIR@')
    conduit.EXTRA_LIB_DIR =         os.path.join(conduit.SHARED_MODULE_DIR, "contrib")

conduit.log("Conduit Installed: %s" % conduit.IS_INSTALLED)
conduit.log("Log Level: %s" % conduit.LOG_LEVEL)

# Start the application
import conduit.MainWindow
conduit.MainWindow.conduit_main()
 
