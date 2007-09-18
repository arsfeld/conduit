#!/usr/bin/env python

import sys
import dbus
import getopt
import os

APPLICATION_DBUS_IFACE="org.conduit.Application"
SYNCSET_DBUS_IFACE="org.conduit.SyncSet"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

def main(useGui, quitWhenFinished, exportFile):
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


    if useGui:
        remote_object = bus.get_object(SYNCSET_DBUS_IFACE,"/syncset/gui")
    else:
        remote_object = bus.get_object(SYNCSET_DBUS_IFACE,"/syncset/dbus")

    ss = dbus.Interface(remote_object, SYNCSET_DBUS_IFACE)

    print "Add the conduit to a SyncSet"
    ss.AddConduit(cond)

    print "Synchronize the conduit"
    cond.Sync()

    #now use the spiffy dbus iface to build a simple export conduit
    if exportFile != None:
        path = app.BuildExporter("TestSink")
        exporter = bus.get_object(CONDUIT_DBUS_IFACE,path)
        #now call into the exporter iface for the export specific tasks
        exporter.AddData(exportFile,dbus_interface=EXPORTER_DBUS_IFACE)
        #and the normal iface to sync
        exporter.Sync(dbus_interface=CONDUIT_DBUS_IFACE)
        
    if quitWhenFinished:
        app.Quit()

def usage():
    usage = "example.py\n" + \
            "Options:\n" + \
            "\t--gui\tShow the conduit (syncset) in the GUI\n" + \
            "\t--quit\tClose conduit when finished"
    print usage
    sys.exit(1)

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "e:gq", ["export=", "gui", "quit"])
    except getopt.GetoptError:
        usage()

    quit = False
    gui = False
    export = None
    for o, a in opts:
        if o in ("-g", "--gui"):
            gui = True
        if o in ("-q", "--quit"):
            quit = True
        if o in ("-e", "--export"):
            export = os.path.abspath(a)

    main(
        useGui=gui,
        quitWhenFinished=quit,
        exportFile=export
        )
