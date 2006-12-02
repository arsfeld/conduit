"""
DBus related functionality including the DBus interface and utility 
functions

Parts of this code adapted from Listen (GPLv2) (c) Mehdi Abaakouk
http://listengnome.free.fr

Copyright: John Stowers, 2006
License: GPLv2
"""
import sys
import random
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import logging
import conduit
from conduit.Synchronization import SyncManager
from conduit.TypeConverter import TypeConverter

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

#Example Message
#dbus-send --session --dest=org.freedesktop.conduit --print-reply /org/freedesktop/conduit org.freedesktop.conduit.Ping
class DBusView(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName(CONDUIT_DBUS_IFACE, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, CONDUIT_DBUS_PATH)
        logging.info("DBus interface initialized")

        self.model = None

        #Store all dataproviders and converters
        self.datasources = []
        self.datasinks = []
        self.conduits = []

        #In order to communicate objects over the bus we instead send
        #a UID which we use to represent them
        self.UIDs = {}

    def _rand(self):
        return random.randint(1, sys.maxint)

    def _print(self, message):
        logging.debug("DBus Message: %s" % message)

    def _on_dataprovider_added(self, loader, dataprovider):
        self.NewDataprovider(dataprovider.classname)

    def set_model(self, model):
        self.model = model
        self.model.connect("dataprovider-added", self._on_dataprovider_added)

        #get the dataproviders
        self.datasources = self.model.get_modules_by_type("source")
        self.datasinks = self.model.get_modules_by_type("sink")

        #initialise the Type Converter
        converters = self.model.get_modules_by_type("converter")
        self.type_converter = TypeConverter(converters)
        #initialise the Synchronisation Manager
        self.sync_manager = SyncManager(self.type_converter)

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Ping(self):
        """
        Test method to check the DBus interface is working
        """
        self._print("Pong")
        return "Pong"

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='as')
    def GetAllDataSources(self):
        self._print("GetAllDataSources")
        return [i.classname for i in self.datasources]

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='as')
    def GetAllDataSinks(self):
        self._print("GetAllDataSinks")
        return [i.classname for i in self.datasinks]

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSource(self, classname):
        self._print("GetDataSource %s" % classname)
        for i in self.datasources:
            if i.classname == classname:
                #Create new instance and add to hashmap etc
                return self._rand()
        return 0

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSink(self, classname):
        self._print("GetDataSink %s" % classname)
        for i in self.datasinks:
            if i.classname == classname:
                #Create new instance and add to hashmap etc
                return self._rand()
        return 0

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='a{ss}')
    def GetDataProviderInformation(self, classname):
        self._print("GetDataProviderInformation %s" % classname)
        info = {}
        for i in self.datasinks + self.datasources:
            if i.classname == classname:
                info["name"] = i.name
                info["description"] = i.description
                info["module_type"] = i.module_type
                info["category"] = i.category
                info["in_type"] = i.in_type
                info["out_type"] = i.out_type
                info["classname"] = i.classname
                info["enabled"] = str(i.enabled)
                info["UID"] = str(i.get_unique_identifier())

        return info

    @dbus.service.method(CONDUIT_DBUS_IFACE)
    def GetAllCompatibleDataSinks(self, classname):
        self._print("GetAllCompatibleDataSinks %s" % classname)
        pass

    @dbus.service.method(CONDUIT_DBUS_IFACE)
    def BuildConduit(self, sourceUID, sinkUID):
        self._print("BuildConduit %s" % classname)
        pass

    @dbus.service.method(CONDUIT_DBUS_IFACE)
    def Sync(self, conduitUID):
        self._print("Sync %s" % classname)
        pass

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def NewDataprovider(self, classname):
        self._print("Emmiting DBus signal NewDataprovider %s" % classname)
