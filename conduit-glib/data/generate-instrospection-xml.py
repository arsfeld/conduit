#!/usr/bin/python
import sys
import dbus

APPLICATION_DBUS_IFACE="org.conduit.Application"
SYNCSET_DBUS_IFACE="org.conduit.SyncSet"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

bus = dbus.SessionBus()

#check conduit is running
obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
avail = dbus_iface.ListNames()

if APPLICATION_DBUS_IFACE not in avail:
    print "Conduit not running"
    sys.exit()
    
#get conduit app
app = bus.get_object(APPLICATION_DBUS_IFACE,"/")

#get a syncset
syncset = bus.get_object(SYNCSET_DBUS_IFACE,"/syncset/gui")

#get a source and a sink
source = bus.get_object(
                DATAPROVIDER_DBUS_IFACE,
                app.GetDataProvider(
                       "TestSource",
                       dbus_interface=APPLICATION_DBUS_IFACE
                       )
                )
sink = bus.get_object(
                DATAPROVIDER_DBUS_IFACE,
                app.GetDataProvider(
                       "TestSink",
                       dbus_interface=APPLICATION_DBUS_IFACE
                       )
                )

#get a conduit
cond = bus.get_object(
                CONDUIT_DBUS_IFACE,
                app.BuildConduit(
                    source, 
                    sink,
                    dbus_interface=APPLICATION_DBUS_IFACE
                    )
                )

FILES = (
    (app,       "application.xml"),
    (syncset,   "syncset.xml"),
    (source,    "dataprovider.xml"),
    (cond,      "conduit.xml"),
)

for obj,name in FILES:
    print "Writing %s" % name
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Introspectable')
    rawxml = iface.Introspect()
    f = open(name, 'w')
    f.write(rawxml)
    f.close()

