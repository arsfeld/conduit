APPNAME="Conduit"
APPVERSION="0.0.1"
SHARED_DATA_DIR = "/usr/share/conduit/data"

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
