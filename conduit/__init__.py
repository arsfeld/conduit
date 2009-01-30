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
DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IS_INSTALLED = not os.path.exists(os.path.join(DIRECTORY,"ChangeLog"))
IS_DEVELOPMENT_VERSION = True

#test the existance of some compulsory directories
CONFIG_DIR = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.environ['HOME'], ".config"))
AUTOSTART_FILE_DIR = os.path.join(CONFIG_DIR,	"autostart")
USER_DIR = os.path.join(CONFIG_DIR,	"conduit")
for d in (AUTOSTART_FILE_DIR, USER_DIR):
    if not os.path.exists(d):
        os.makedirs(d)

if IS_INSTALLED:
    from defs import *
    if not PYTHONDIR in sys.path:
        sys.path.insert(0, PYTHONDIR)
else:
    VERSION =                   "0.3.16"
    LOCALE_DIR =                os.path.join(DIRECTORY, "po")
    SHARED_DATA_DIR =           os.path.join(DIRECTORY, "data")
    SHARED_MODULE_DIR =         os.path.join(DIRECTORY, "conduit", "modules")
    DESKTOP_FILE_DIR =          os.path.join(DIRECTORY, "data")
                                #{GnomeVfs, GIO, Python}
    FILE_IMPL =                 os.environ.get("CONDUIT_FILE_IMPL","GIO")
                                #{gtkmozembed, webkit, system}
    BROWSER_IMPL =              os.environ.get("CONDUIT_BROWSER_IMPL","webkit")
                                #{GConf,Python}
    SETTINGS_IMPL =             os.environ.get("CONDUIT_SETTINGS_IMPL","GConf")

import Globals
GLOBALS = Globals.Globals()

