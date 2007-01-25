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

#Example Message
#   dbus-send --session --dest=org.freedesktop.conduit \
#       --print-reply / org.freedesktop.conduit.Ping
class DBusView(dbus.service.Object):
    def __init__(self):
        bus_name = dbus.service.BusName(CONDUIT_DBUS_IFACE, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, CONDUIT_DBUS_PATH)
        logging.info("DBus interface initialized")

        self.model = None

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
        self.NewDataprovider(dataprovider.get_key())

    def _on_sync_started(self, thread):
        pass

    def _on_sync_completed(self, thread):
        """
        Signal received when a sync finishes
        """
        for i in self.UIDs:
            if self.UIDs[i] == thread.conduit:
                #Send the DBUS signal
                self.SyncCompleted(i)

    #FIXME: More args
    def _on_sync_conflict(self, thread, source, sourceData, sink, sinkData, validChoices):
        conduit = thread.conduit
        for i in self.UIDs:
            if self.UIDs[i] == conduit:
                #Send the DBUS signal
                self.Conflict(i)      

    def _add_dataprovider(self, key, store):
        """
        Instantiates a new dataprovider (source or sink), storing it
        appropriately.
        @param key: Class name of the DP to create
        @param store: self.datasinks or self.datasource
        @returns: The UID of the DP or ERROR on error
        """
        uid = ERROR
        for i in store:
            if i.get_key() == key:
                #Create new instance and add to hashmap etc
                new = self.model.get_new_module_instance(key)
                if new != None:
                    uid = self._rand()
                    #store hash pointing to object instance
                    self.UIDs[uid] = new
        return uid

    def _get_sources(self):
        datasources = self.model.get_modules_by_type("source")
        twoways = self.model.get_modules_by_type("twoway")
        return datasources + twoways

    def _get_sinks(self):
        datasinks = self.model.get_modules_by_type("sink")
        twoways = self.model.get_modules_by_type("twoway")
        return datasinks + twoways

    def _get_all_dps(self):
        datasources = self.model.get_modules_by_type("source")
        datasinks = self.model.get_modules_by_type("sink")
        twoways = self.model.get_modules_by_type("twoway")
        return datasources + datasinks + twoways

    def set_model(self, model):
        self.model = model
        self.model.connect("dataprovider-added", self._on_dataprovider_added)

        #initialise the Type Converter
        self.type_converter = TypeConverter(self.model)
        #initialise the Synchronisation Manager
        self.sync_manager = SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({"conflict":"skip","missing":"skip"})
        self.sync_manager.add_syncworker_callbacks(
                                self._on_sync_started, 
                                self._on_sync_completed, 
                                self._on_sync_conflict
                                )

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
        #get the dataproviders
        return [i.get_key() for i in self._get_sources()]

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='as')
    def GetAllDataSinks(self):
        self._print("GetAllDataSinks")
        return [i.get_key() for i in self._get_sinks()]

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSource(self, key):
        self._print("GetDataSource %s" % key)
        return self._add_dataprovider(key, self._get_sources())

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSink(self, key):
        self._print("GetDataSink %s" % key)
        return self._add_dataprovider(key, self._get_sinks())        

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='s', out_signature='a{ss}')
    def GetDataProviderInformation(self, key):
        self._print("GetDataProviderInformation %s" % key)
        info = {}
        for i in self._get_all_dps():
            if i.get_key() == key:
                info["name"] = i.name
                info["description"] = i.description
                info["module_type"] = i.module_type
                info["category"] = i.category
                info["in_type"] = i.in_type
                info["out_type"] = i.out_type
                info["classname"] = i.classname
                info["key"] = i.get_key()
                info["enabled"] = str(i.enabled)
                info["UID"] = i.get_UID()

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
        for s in self._get_sinks():
            if s.enabled == True:
                out = self.UIDs[sourceUID].out_type
                if s.in_type == out:
                    compat.append(s.get_key())
                elif self.type_converter.conversion_exists(out, s.in_type):
                    compat.append(s.get_key())

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
    def NewDataprovider(self, key):
        self._print("Emmiting DBus signal NewDataprovider %s" % key)

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def SyncCompleted(self, conduitUID):
        self._print("Emmiting DBus signal SyncCompleted %s" % conduitUID)

    @dbus.service.signal(CONDUIT_DBUS_IFACE)
    def Conflict(self):
        self._print("Emmiting DBus signal Conflict")
