"""
DBus related functionality including the DBus interface and utility 
functions

Parts of this code adapted from Listen (GPLv2) (c) Mehdi Abaakouk
http://listengnome.free.fr

Copyright: John Stowers, 2006
License: GPLv2
"""
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import logging
import conduit

CONDUIT_DBUS_PATH = "/org/freedesktop/conduit"
CONDUIT_DBUS_IFACE = "org.freedesktop.conduit"

def dbus_service_available(bus,interface):
    try: 
        import dbus
    except: 
        return False
    obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
    dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus') 
    avail = dbus_iface.ListNames()
    return interface in avail

class DBusView(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName(CONDUIT_DBUS_IFACE, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, CONDUIT_DBUS_PATH)
        logging.info("DBus interface initialized")

        self.model = None

    def set_model(self, model):
        self.model = model

    @dbus.service.method(CONDUIT_DBUS_IFACE)
    def hello(self):
        print "Hello"        
        return "hello"

    @dbus.service.method(CONDUIT_DBUS_IFACE)
    def play(self,uris):
        print "DBUS: play()"
        return "Successful command "

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def enqueue(self,uris):
        print "DBUS: enqueue()"
        return "Successful command "

