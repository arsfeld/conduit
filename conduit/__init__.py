APPNAME="Conduit"
APPVERSION="0.0.0"
#for pixmaps, glade files, etc
SHARED_DATA_DIR = "/usr/share/conduit/data"
GLADE_FILE = "/usr/share/conduit/data/conduit.glade"
#for the dynamically loaded modules
SHARED_MODULE_DIR = "/usr/share/conduit/modules"
USER_MODULE_DIR = "~/.conduit/modules"

DEBUG=False

from DataProviderView import DataProviderView
from DataType import DataType
from TypeConverter import TypeConverter
from SyncManager import SyncManager
from MainWindow import MainWindow
from ConduitEditorCanvas import ConduitEditorCanvas
from DataProvider import DataProviderModel, DataSource, DataSink
from ModuleManager import ModuleManager, ModuleLoader, ModuleWrapper, DataProviderTreeView, DataProviderTreeModel

# Make sure epydoc documents the classes 
# as part of the barracuda module
__all__ = ["DataProviderView", "DataType", "MainWindow", "ConduitEditorCanvas", "DataProviderModel", "DataSource", "DataSink", "ModuleManager", "ModuleLoader", "ModuleWrapper", "DataProviderTreeView", "DataProviderTreeModel", "TypeConverter"]
