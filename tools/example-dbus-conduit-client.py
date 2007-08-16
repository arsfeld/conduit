#!/usr/bin/env python

import sys
import dbus

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
UPLOADER_DBUS_IFACE="org.conduit.Upload"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

def main():
    bus = dbus.SessionBus()

    #Create an Interface wrapper for the remote object
    remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
    app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)

    #get a dataprovider
    path = app.GetDataProvider("TestSource")
    source = dbus.Interface(
                bus.get_object(DATAPROVIDER_DBUS_IFACE,path),
                DATAPROVIDER_DBUS_IFACE
                )

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

    print source.GetConfigurationXml()
    #cond.Sync()
    #print app.GetAllDataProviders()
    #

    if "--quit" in sys.argv[1:]:
        app.Quit()

if __name__ == '__main__':
    main()
