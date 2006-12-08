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
from conduit.Conduit import Conduit

CONDUIT_DBUS_PATH = "/"
CONDUIT_DBUS_IFACE = "org.freedesktop.conduit"

ERROR = -1
SUCCESS = 0

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
#   dbus-send --session --dest=org.freedesktop.conduit \
#       --print-reply / org.freedesktop.conduit.Ping
class DBusView(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName(CONDUIT_DBUS_IFACE, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, CONDUIT_DBUS_PATH)
        logging.info("DBus interface initialized")

        self.model = None

        #Store all loaded dataproviders and converters
        self.datasources = []
        self.datasinks = []

        #Store user constructed conduits
        self.conduits = []

        #In order to communicate objects over the bus we instead send
        #a UID which we use to represent them
        self.UIDs = {}

    def _rand(self):
        rand = random.randint(1, sys.maxint)
        #Guarentee uniqueness
        while rand in self.UIDs:
            rand = random.randint(1, sys.maxint)
        return rand

    def _print(self, message):
        logging.debug("DBus Message: %s" % message)

    def _on_dataprovider_added(self, loader, dataprovider):
        self.NewDataprovider(dataprovider.classname)

    def _on_sync_finished(self, conduit):
        """
        Signal received when a sync finishes
        """
        for i in self.UIDs:
            if self.UIDs[i] == conduit:
                #Send the DBUS signal
                self.SyncFinished(i)

    #FIXME: More args
    def _on_sync_conflict(self, thread, source, sourceData, sink, sinkData, validChoices):
        conduit = thread.conduit
        for i in self.UIDs:
            if self.UIDs[i] == conduit:
                #Send the DBUS signal
                self.Conflict(i)      

    def _add_dataprovider(self, classname, store):
        """
        Instantiates a new dataprovider (source or sink), storing it
        appropriately.
        @param classname: Class name of the DP to create
        @param store: self.datasinks or self.datasource
        @returns: The UID of the DP or ERROR on error
        """
        uid = ERROR
        for i in store:
            if i.classname == classname:
                #Create new instance and add to hashmap etc
                new = self.model.get_new_module_instance(classname)
                if new != None:
                    uid = self._rand()
                    #store hash pointing to object instance
                    self.UIDs[uid] = new
        return uid

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
        self.sync_manager.set_twoway_policy({"conflict":"skip","missing":"skip"})
        self.sync_manager.set_sync_callbacks(self._on_sync_finished, self._on_sync_conflict)

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='i')
    def Ping(self):
        """
        Test method to check the DBus interface is working
        """
        self._print("Ping")
        return SUCCESS

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
        return self._add_dataprovider(classname, self.datasources)

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSink(self, classname):
        self._print("GetDataSink %s" % classname)
        return self._add_dataprovider(classname, self.datasinks)        

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

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='i', out_signature='as')
    def GetAllCompatibleDataSinks(self, sourceUID):
        """
        Gets all datasinks compatible with the supplied datasource. Compatible 
        is defined as;
        1) Enabled
        2) sink.in_type == source.out_type OR
        3) Conversion is available
        """
        self._print("GetAllCompatibleDataSinks %s" % sourceUID)
        compat = []
        if sourceUID not in self.UIDs:
            return compat

        #look for enabled datasinks
        for s in self.datasinks:
            if s.enabled == True:
                out = self.UIDs[sourceUID].out_type
                if s.in_type == out:
                    compat.append(s.classname)
                elif self.type_converter.conversion_exists(out, s.in_type):
                    compat.append(s.classname)

        return compat

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='ii', out_signature='i')
    def BuildConduit(self, sourceUID, sinkUID):
        self._print("BuildConduit %s:%s" % (sourceUID, sinkUID))
        uid = ERROR
        if sourceUID in self.UIDs and sinkUID in self.UIDs:
            #create new conduit, populate and add to hashmap
            uid = self._rand()
            conduit = Conduit()
            conduit.add_dataprovider_to_conduit(self.UIDs[sourceUID])
            conduit.add_dataprovider_to_conduit(self.UIDs[sinkUID])
            self.UIDs[uid] = conduit
        return uid

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='ss', out_signature='i')
    def SetSyncPolicy(self, conflictPolicy, missingPolicy):
        self._print("SetSyncPolicy (conflict:%s missing:%s)" % (conflictPolicy, missingPolicy))
        allowedPolicy = ["ask", "replace", "skip"]
        if conflictPolicy not in allowedPolicy:
            return ERROR
        if missingPolicy not in allowedPolicy:
            return ERROR

        self.sync_manager.set_twoway_policy({
                "conflict"  :   conflictPolicy,
                "missing"   :   missingPolicy}
                )
        return SUCCESS


    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='i', out_signature='i')
    def Sync(self, conduitUID):
        self._print("Sync %s" % conduitUID)
        if conduitUID in self.UIDs:
            self.sync_manager.sync_conduit(self.UIDs[conduitUID])
            return SUCCESS
        else:
            return ERROR

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def NewDataprovider(self, classname):
        self._print("Emmiting DBus signal NewDataprovider %s" % classname)

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def SyncFinished(self, conduitUID):
        self._print("Emmiting DBus signal SyncFinished %s" % conduitUID)

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def Conflict(self):
        self._print("Emmiting DBus signal Conflict")
