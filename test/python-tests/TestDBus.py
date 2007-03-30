#common sets up the conduit environment
from common import *

import os
import dbus
import sys
import time

CONDUIT_DBUS_PATH = "/"
CONDUIT_DBUS_IFACE = "org.gnome.Conduit"

bus = dbus.SessionBus()
obj = bus.get_object(CONDUIT_DBUS_IFACE, CONDUIT_DBUS_PATH)
remoteConduit = dbus.Interface(obj, CONDUIT_DBUS_IFACE)

def dbus_service_available(bus,interface):
    obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
    dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
    avail = dbus_iface.ListNames()
    return interface in avail

#Start the conduit process
APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "conduit", "start_conduit.py"))
pid = os.spawnlp(os.P_NOWAIT, "python", "python", APP, "--console")

#wait for it to startup
MAX_WAIT = 5
i = 0
while i < MAX_WAIT:
    if dbus_service_available(bus,CONDUIT_DBUS_IFACE):
        break
    time.sleep(1)
    i += 1

ok ("checking conduit DBus is available", i != MAX_WAIT)
#Check DBUS service available
#Test the searches
ok ("searching for TestSource", "TestSource" in remoteConduit.GetAllDataSources() )
ok ("searching for TestSink", "TestSink" in remoteConduit.GetAllDataSinks() )
#Set sync policy
ok ("setting sync policy", remoteConduit.SetSyncPolicy("ask","ask") )
#Make a datasource and datasink
source = remoteConduit.GetDataSource("TestSource")
ok("creating datasource", source)
sink = remoteConduit.GetDataSink("TestSink")
ok("creating datasink", sink)
#check TestSink is a compatible sink
ok ("checking TestSink is a compatible datasink", "TestSink" in remoteConduit.GetAllCompatibleDataSinks(source) )
#add them to a conduit
conduit = remoteConduit.BuildConduit(source, sink)
ok("adding to conduit", conduit)
#synchronize
ok("synchronizing", remoteConduit.Sync(conduit) )
#now add a conflicting sink to the fray
conflictsink = remoteConduit.GetDataSink("TestConflict")
ok("creating conflict datasink", conflictsink)
#add them to a conduit
ok("adding 2nd sink to conduit", remoteConduit.AddSinkToConduit(conduit, conflictsink) )
#synchronize
ok("synchronizing", remoteConduit.Sync(conduit) )
#quit
ok("Quitting", remoteConduit.Quit() )

waitpid(pid,0)

