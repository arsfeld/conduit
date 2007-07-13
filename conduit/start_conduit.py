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
import sys
import os, os.path

# Look for ChangeLog to see if we are installed
directory = os.path.join(os.path.dirname(__file__), '..')
changelog = os.path.join(directory,"ChangeLog")
if os.path.exists(changelog):
    #UNINSTALLED
    sys.path.insert(0, os.path.abspath(directory))
    import conduit
else:
    #INSTALLED
    #Support alternate install paths   
    if not '@PYTHONDIR@' in sys.path:
        sys.path.insert(0, '@PYTHONDIR@')
    import conduit
    conduit.IS_INSTALLED =          True
    conduit.APPVERSION =            '@VERSION@'
    conduit.LOCALE_DIR =            os.path.abspath('@LOCALEDIR@')
    conduit.SHARED_DATA_DIR =       os.path.abspath('@PKGDATADIR@')
    conduit.GLADE_FILE =            os.path.join(conduit.SHARED_DATA_DIR, "conduit.glade")
    conduit.SHARED_MODULE_DIR =     os.path.abspath('@PKGLIBDIR@')
    conduit.EXTRA_LIB_DIR =         os.path.join(conduit.SHARED_MODULE_DIR, "contrib")

#Development versions are X.ODD_VERSION.Y
conduit.IS_DEVELOPMENT_VERSION = int(conduit.APPVERSION.split('.')[1]) % 2 == 1

#set up the gettext system and locales
from gtk import glade
import gettext

for module in glade, gettext:
    module.bindtextdomain('conduit', conduit.LOCALE_DIR)
    module.textdomain('conduit')

# Start the application
import conduit.MainWindow
app = conduit.MainWindow.Application()
 
