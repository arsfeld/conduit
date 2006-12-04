#!/usr/bin/python
import dbus

CONDUIT_DBUS_PATH = "/"
CONDUIT_DBUS_IFACE = "org.freedesktop.conduit"

bus = dbus.SessionBus()
obj = bus.get_object(CONDUIT_DBUS_IFACE, CONDUIT_DBUS_PATH)
remoteConduit = dbus.Interface(obj, CONDUIT_DBUS_IFACE)

#Make a datasource and datasink
source = remoteConduit.GetDataSource("TestSource")
sink = remoteConduit.GetDataSink("TestSink")
#add them to a conduit
conduit = remoteConduit.BuildConduit(source, sink)
#synchronize
remoteConduit.Sync(conduit)


