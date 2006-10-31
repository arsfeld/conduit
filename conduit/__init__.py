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
import gobject

APPNAME="Conduit"
APPVERSION="0.3.0"
USER_DIR = os.path.join(os.environ['HOME'],".conduit")
if not os.path.exists(USER_DIR):
    os.mkdir(USER_DIR)
#The following variables are empty only as placeholders.
#they are filled out in start_conduit.py based upon whether conduit is
#installed or not
SHARED_DATA_DIR = "" #for pixmaps, glade files, etc
GLADE_FILE = ""
SHARED_MODULE_DIR = "" #for the dynamically loaded modules
EXTRA_LIB_DIR = "" #Dir where 3rd party libraries live if shipped with conduit
IS_INSTALLED = False #Can be used to determine if the app is running installed or not

# If the CONDUIT_LOGLEVEL evironment variable is set then this 
#overrides the settings below
DEFAULT_LOG_LEVEL = "DEBUG"

LOG_DICT = {"INFO" : logging.INFO,
            "DEBUG" : logging.DEBUG,
            "WARNING" : logging.WARNING,
            "ERROR" : logging.ERROR,
            "CRITICAL" : logging.CRITICAL
            }
    
try:
    LOG_LEVEL = os.environ['CONDUIT_LOGLEVEL']
    level=LOG_DICT[LOG_LEVEL]
except KeyError:
    LOG_LEVEL = DEFAULT_LOG_LEVEL
    level = LOG_DICT[LOG_LEVEL]

print "Log Level =", LOG_LEVEL
logging.basicConfig(level=level,
                    format='[%(levelname)s] %(message)s (%(filename)s)')
#                    filename='/tmp/myapp.log',
#                    filemode='w')

from TypeConverter import TypeConverter
from MainWindow import MainWindow
from Canvas import Canvas
from DataProvider import DataProviderBase, DataSource, DataSink, DataProviderTreeView, DataProviderTreeModel
from Module import ModuleLoader, ModuleWrapper
from Conduit import Conduit
from Exceptions import ConversionError, RefreshError, SyncronizeError, SyncronizeFatalError, SynchronizeConflictError, StopSync,  ConversionDoesntExistError
from Synchronization import SyncManager, SyncWorker
from Settings import Settings

# Make sure epydoc documents the classes 
# as part of the conduit module
__all__ = ["MainWindow", "Canvas", "DataProviderBase", "DataSource", "DataSink", "ModuleLoader", "ModuleWrapper", "DataProviderTreeView", "DataProviderTreeModel", "TypeConverter", "Conduit", "SyncManager", "SyncWorker", "Settings"]

gobject.threads_init()
settings = Settings()
