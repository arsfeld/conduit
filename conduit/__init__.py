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

import logging
import os

APPNAME="Conduit"
APPVERSION="0.0.0"
#for pixmaps, glade files, etc
SHARED_DATA_DIR = "/usr/share/conduit/data"
GLADE_FILE = "/usr/share/conduit/data/conduit.glade"
#for the dynamically loaded modules
SHARED_MODULE_DIR = "/usr/share/conduit/modules"
USER_MODULE_DIR = "~/.conduit/modules"

# If the CONDUIT_LOGLEVEL evironment variable is set then this 
#overrides the settings below
DEFAULT_LOGLEVEL = "DEBUG"

try:
    LOG_LEVEL = os.environ['CONDUIT_LOGLEVEL']
except KeyError:
    LOG_LEVEL = DEFAULT_LOGLEVEL
    pass
    
LOG_DICT = {"INFO" : logging.INFO,
            "DEBUG" : logging.DEBUG,
            "WARNING" : logging.WARNING,
            "ERROR" : logging.ERROR,
            "CRITICAL" : logging.CRITICAL
            }
    
if LOG_LEVEL not in LOG_DICT.keys():
    LOG_LEVEL = DEFAULT_LOGLEVEL
 
print "Log Level = ", LOG_LEVEL
logging.basicConfig(level=LOG_DICT[LOG_LEVEL],
                    format='[%(levelname)s] %(message)s (%(filename)s)')
#                    filename='/tmp/myapp.log',
#                    filemode='w')

from TypeConverter import TypeConverter
from MainWindow import MainWindow
from Canvas import Canvas
from DataProvider import DataProviderBase, DataSource, DataSink, DataProviderTreeView, DataProviderTreeModel
from Module import ModuleLoader, ModuleWrapper
from Conduit import Conduit
from Exceptions import ConversionError, RefreshError, SyncronizeError, SyncronizeFatalError, SynchronizeConflictError, StopSync
from Synchronization import SyncManager, SyncWorker

# Make sure epydoc documents the classes 
# as part of the conduit module
__all__ = ["MainWindow", "Canvas", "DataProviderBase", "DataSource", "DataSink", "ModuleLoader", "ModuleWrapper", "DataProviderTreeView", "DataProviderTreeModel", "TypeConverter", "Conduit", "SyncManager", "SyncWorker"]

import gobject
gobject.threads_init()
