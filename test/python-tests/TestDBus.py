#common sets up the conduit environment
from common import *
from conduit.DBus import *

#Call the DBus functions directly so that we get code coverage analysis
#See example-dbus-conduit-client.py file for and example of the DBus iface

test = SimpleTest()

dbus = DBusView(None, test.model, test.type_converter)

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
ok("Got TestSink", sink != None)

cond = dbus.BuildConduit(source.get_path(), sink.get_path())
ok("Got Conduit", cond != None)

cond.Refresh()
cond.Sync()


