#!/usr/bin/python
import dbus
import sys

CONDUIT_DBUS_PATH = "/"
CONDUIT_DBUS_IFACE = "org.freedesktop.conduit"

bus = dbus.SessionBus()
obj = bus.get_object(CONDUIT_DBUS_IFACE, CONDUIT_DBUS_PATH)
remoteConduit = dbus.Interface(obj, CONDUIT_DBUS_IFACE)

def ok(message, code):
    if type(code) == int:
        if code == -1:
            print "[FAIL] %s" % message
            sys.exit()
        else:
            print "[PASS] %s" % message
            return code
    elif type(code) == bool:
        if code == True:
            print "[PASS] %s" % message
        else:
            print "[FAIL] %s" % message
            sys.exit()

def dbus_service_available(bus,interface):
    obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
    dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
    avail = dbus_iface.ListNames()
    return interface in avail

#Check DBUS service available
ok ("checking conduit DBus is available", dbus_service_available(bus,CONDUIT_DBUS_IFACE) )
ok ("checking DBus working", remoteConduit.Ping() )
#Test the searches
ok ("searching for TestSource", "TestSource" in remoteConduit.GetAllDataSources() )
ok ("searching for TestSink", "TestSink" in remoteConduit.GetAllDataSinks() )
#Set sync policy
ok ("setting sync policy", remoteConduit.SetSyncPolicy("ask","ask") )
#Make a datasource and datasink
source =    ok( "creating datasource", remoteConduit.GetDataSource("TestSource") )
sink =      ok( "creating datasink", remoteConduit.GetDataSink("TestSink") )
#check TestSink is a compatible sink
ok ("checking TestSink is a compatible datasink", "TestSink" in remoteConduit.GetAllCompatibleDataSinks(source) )
#add them to a conduit
conduit =   ok( "adding to conduit", remoteConduit.BuildConduit(source, sink) )
#synchronize
ok( "synchronizing", remoteConduit.Sync(conduit) )


