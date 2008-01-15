"""
Introduction
============
    Conduit is a synchronization solution for GNOME which allows the user to 
    take their emails, files, bookmarks, and any other type of personal 
    information and synchronize that data with another computer, an online 
    service, or even another electronic device.

Conduit manages the synchronization and conversion of data into other formats. 
For example, conduit allows you to;

 1. Synchronize your tomboy notes to a file on a remote computer
 2. Synchronize your emails to your mobile phone
 3. Synchronize your bookmarks to delicious, gmail, or even your own webserver
 4. and many more... 

Any combination you can imagine, Conduit will take care of the conversion 
and synchronization. 

Copyright: John Stowers, 2006
License: GPLv2
"""
import os
import gobject
import sys
gobject.threads_init()

################################################################################
# Global Constants
################################################################################
_dirname = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IS_INSTALLED = not os.path.exists(os.path.join(_dirname,"ChangeLog"))
IS_DEVELOPMENT_VERSION = True

# Check the profile directory to prevent crashes when saving settings, etc
USER_DIR = os.path.join(os.environ['HOME'],".conduit")
if not os.path.exists(USER_DIR):
    os.mkdir(USER_DIR)

if IS_INSTALLED:
    from defs import *
    if not PYTHONDIR in sys.path:
        sys.path.insert(0, PYTHONDIR)
else:
    APPNAME =                   "Conduit"
    APPVERSION =                "0.3.6"
    LOCALE_DIR =                os.path.join(_dirname, "po")
    SHARED_DATA_DIR =           os.path.join(_dirname, "data")
    GLADE_FILE =                os.path.join(_dirname, "data","conduit.glade")
    SHARED_MODULE_DIR =         os.path.join(_dirname, "conduit", "modules")

import Globals
GLOBALS = Globals.Globals()

