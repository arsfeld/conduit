#!/usr/bin/env python

import sys
import dbus

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

def main():
    bus = dbus.SessionBus()

    #Create an Interface wrapper for the remote object
    remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
    app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)

    dps = app.GetAllDataProviders()
    print "Available DPs"
    for dp in dps:
        print " * ",dp

    #get a dataprovider
    path = app.GetDataProvider("TestSource")
    source = dbus.Interface(
                bus.get_object(DATAPROVIDER_DBUS_IFACE,path),
                DATAPROVIDER_DBUS_IFACE
                )

    print "Source Configuration"
    print source.GetConfigurationXml()

    #get another
    path = app.GetDataProvider("TestSink")
    sink = dbus.Interface(
                bus.get_object(DATAPROVIDER_DBUS_IFACE,path),
                DATAPROVIDER_DBUS_IFACE
                )

    #get a conduit
    path = app.BuildConduit(source, sink)
    cond = dbus.Interface(
                bus.get_object(CONDUIT_DBUS_IFACE,path),
                CONDUIT_DBUS_IFACE
                )


    print "Synchronize the conduit"
    cond.Sync()

    #now use the spiffy dbus iface to build a simple export conduit
    path = app.BuildExporter("TestSink")
    exporter = bus.get_object(CONDUIT_DBUS_IFACE,path)
    #now call into the exporter iface for the export specific tasks
    exporter.AddData("/home/john/Desktop/screenshot.png",dbus_interface=EXPORTER_DBUS_IFACE)
    exporter.AddData("/usr/local/bin/",dbus_interface=EXPORTER_DBUS_IFACE)
    #and the normal iface to sync
    exporter.Sync(dbus_interface=CONDUIT_DBUS_IFACE)
    #and the normal iface to sync

    if "--quit" in sys.argv[1:]:
        app.Quit()

if __name__ == '__main__':
    main()
