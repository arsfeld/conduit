#common sets up the conduit environment
from common import *
from conduit.DBus import *

#Call the DBus functions directly so that we get code coverage analysis
#See example-dbus-conduit-client.py file for and example of the DBus iface
#Note: A few small hacks are needed to acomplish this, get_path() and SENDER
SENDER="TestDBus.py"

#Hack to simulate getting a DBus object at a given path (ignores iface)
# remote_object = bus.get_object(IFACE_IGNORED,"/path/to/obj")
# obj = dbus.Interface(remote_object, IFACE_IGNORED)
# return obj
def get_dbus_object(path):
    return EXPORTED_OBJECTS[path]

test = SimpleTest()
DBusInterface(
        conduitApplication=None,
        moduleManager=test.model,
        typeConverter=test.type_converter,
        syncManager=test.sync_manager,
        guiSyncSet=test.sync_set,
        dbusSyncSet=None)
        
dbus = get_dbus_object("/")

alldps = dbus.GetAllDataProviders()
ok("Got all DPs", len(alldps) > 0)

source = dbus.GetDataProvider("TestSource")
ok("Got TestSource", source != None)

config = source.GetConfigurationXml()
ok("Got TestSource Config", config != "")

info = source.GetInformation()
ok("Got TestSource Information", info != "")

source.SetConfigurationXml(config)
ok("Set TestSource Config", True)

source.AddData("Foo")
ok("Add data to TestSource", True)

sink = dbus.GetDataProvider("TestSink")
ok("Got TestSink", not sink.IsPending())

#test the exporter interface
cond = dbus.BuildExporter("TestSink", SENDER)
ok("Exporter iface: Got conduit", cond != None)

config = cond.SinkGetConfigurationXml()
ok("Exporter iface: Got sink config", config != "")

cond.SinkSetConfigurationXml(config)
ok("Exporter iface: Set sink config", True)

info = cond.SinkGetInformation()
ok("Exporter iface: Got sink info", info != "")

cond.AddData("Foo")
ok("Exporter iface: add data", True)

#construct a normal conduit
cond = dbus.BuildConduit(source.get_path(), sink.get_path(), SENDER)
ok("Got Conduit", cond != None)

#add some more sinks
try:
    sink = dbus.GetDataProvider("TestSink")
    cond.AddDataprovider(sink.get_path(), False)
    ok("Added extra sink", True)
except:
    ok("Added extra sink", False)

try:
    sink = dbus.GetDataProvider("TestTwoWay")
    cond.AddDataprovider(sink.get_path(), False)
    cond.DeleteDataprovider(sink.get_path())
    ok("Added and deleted extra sink", True)
except:
    ok("Added and deleted extra sink", False)

sink = dbus.GetDataProvider("Foobar")
ok("Pending dps identified", sink.IsPending())

try:
    cond.Refresh()
    ok("Refresh conduit", True)
except:
    ok("Refresh conduit", False)

try:
    cond.Sync()
    ok("Sync conduit", True)
except:
    ok("Sync conduit", False)

#test the syncset interface
ss = get_dbus_object("/syncset/gui")
ss.AddConduit(cond.get_path())
ok("Add Conduit to SyncSet", True)

ss.DeleteConduit(cond.get_path())
ok("Delete Conduit from SyncSet", True)


finished()
