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
DEFAULT_LOG_LEVEL = "DEBUG"

try:
    LOG_LEVEL = os.environ['CONDUIT_LOGLEVEL']
except KeyError:
    LOG_LEVEL = DEFAULT_LOG_LEVEL
    pass
    
LOG_DICT = {"INFO" : logging.INFO,
            "DEBUG" : logging.DEBUG,
            "WARNING" : logging.WARNING,
            "ERROR" : logging.ERROR,
            "CRITICAL" : logging.CRITICAL
            }
    
if LOG_LEVEL not in LOG_DICT.keys():
    LOG_LEVEL = DEFAULT_LOG_LEVEL
 
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

# Make sure epydoc documents the classes 
# as part of the conduit module
__all__ = ["MainWindow", "Canvas", "DataProviderBase", "DataSource", "DataSink", "ModuleLoader", "ModuleWrapper", "DataProviderTreeView", "DataProviderTreeModel", "TypeConverter", "Conduit"]
