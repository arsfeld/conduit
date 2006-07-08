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

from DataProviderView import DataProviderView
from DataType import DataType
from TypeConverter import TypeConverter
from SyncManager import SyncManager
from MainWindow import MainWindow
from ConduitEditorCanvas import ConduitEditorCanvas
from DataProvider import DataProviderModel, DataSource, DataSink
from ModuleManager import ModuleManager, ModuleLoader, ModuleWrapper, DataProviderTreeView, DataProviderTreeModel

# Make sure epydoc documents the classes 
# as part of the conduit module
__all__ = ["DataProviderView", "DataType", "MainWindow", "ConduitEditorCanvas", "DataProviderModel", "DataSource", "DataSink", "ModuleManager", "ModuleLoader", "ModuleWrapper", "DataProviderTreeView", "DataProviderTreeModel", "TypeConverter"]
