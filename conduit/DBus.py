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
import gtk
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import conduit
from conduit import log,logd,logw
from conduit.Synchronization import SyncManager
from conduit.TypeConverter import TypeConverter
from conduit.Conduit import Conduit

ERROR = -1
SUCCESS = 0

#Example Message
#   dbus-send --session --dest=org.gnome.Conduit \
#       --print-reply / org.gnome.Conduit.Ping
class DBusView(dbus.service.Object):
    def __init__(self, conduitApplication):
        bus_name = dbus.service.BusName(conduit.DBUS_IFACE, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, "/")
        log("DBus interface initialized")

        self.conduitApplication = conduitApplication

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
        logd("DBus Message: %s" % message)

    def _on_dataprovider_added(self, loader, dataprovider):
        self.DataproviderAvailable(dataprovider.get_key())

    def _on_dataprovider_removed(self, loader, dataprovider):
        self.DataproviderUnavailable(dataprovider.get_key())

    def _on_data_changed(self, sender, key):
        self.DataproviderChanged(key)

    def _on_sync_started(self, thread):
        pass

    def _on_sync_completed(self, thread, error):
        """
        Signal received when a sync finishes
        """
        for i in self.UIDs:
            if self.UIDs[i] == thread.conduit:
                #Send the DBUS signal
                self.SyncCompleted(i, bool(error))

    def _on_sync_progress(self, thread, conduit, progress):
        """
        Signal received when a sync finishes
        """
        for i in self.UIDs:
            if self.UIDs[i] == conduit:
                #Send the DBUS signal
                self.SyncProgress(i,float(progress))

    #FIXME: More args
    def _on_sync_conflict(self, thread, source, sourceData, sink, sinkData, validChoices, isDeleted):
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
                    #connect to signals
                    new.module.connect("change-detected", self._on_data_changed, key)
        return uid

    def _add_conduit(self, sourceUID, sinkUID):
        uid = ERROR
        if sourceUID in self.UIDs and sinkUID in self.UIDs:
            #create new conduit, populate and add to hashmap
            uid = self._rand()
            conduit = Conduit()
            conduit.add_dataprovider_to_conduit(self.UIDs[sourceUID])
            conduit.add_dataprovider_to_conduit(self.UIDs[sinkUID])
            self.UIDs[uid] = conduit
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
        self.model.connect("dataprovider-removed", self._on_dataprovider_removed)

        #initialise the Type Converter
        self.type_converter = TypeConverter(self.model)
        #initialise the Synchronisation Manager
        self.sync_manager = SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({"conflict":"skip","deleted":"skip"})
        self.sync_manager.add_syncworker_callbacks(
                                self._on_sync_started, 
                                self._on_sync_completed, 
                                self._on_sync_conflict,
                                self._on_sync_progress
                                )

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='ss', out_signature='iii')
    def BuildOneWaySync(self, sourceKey, sinkKey):
        self._print("BuildOneWaySync %s --> %s" % (sourceKey, sinkKey))
        source = self._add_dataprovider(sourceKey, self._get_sources())
        sink = self._add_dataprovider(sinkKey, self._get_sinks())
        conduit = self._add_conduit(source, sink)
        if conduit != ERROR:
            self.UIDs[conduit].disable_two_way_sync()
        return conduit, source, sink

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='ss', out_signature='iii')
    def BuildTwoWaySync(self, sourceKey, sinkKey):
        self._print("BuildTwoWaySync %s <-> %s" % (sourceKey, sinkKey))
        source = self._add_dataprovider(sourceKey, self._get_sources())
        sink = self._add_dataprovider(sinkKey, self._get_sinks())
        conduit = self._add_conduit(source, sink)
        if conduit != ERROR:
            self.UIDs[conduit].enable_two_way_sync()
        return conduit, source, sink

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='ss', out_signature='iii')
    def BuildSimpleExport(self, sinkKey, sinkConfigXml):
        self._print("BuildSimpleExport --> %s" % sinkKey)
        source = self._add_dataprovider("FileSource", self._get_sources())
        sink = self._add_dataprovider(sinkKey, self._get_sinks())
        if sink != ERROR:
            self.UIDs[sink].module.set_configuration_xml(sinkConfigXml)
        conduit = self._add_conduit(source, sink)
        if conduit != ERROR:
            self.UIDs[conduit].enable_two_way_sync()
        return conduit, source, sink

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='i')
    def Quit(self):
        #sessionBus = dbus.SessionBus()
        #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
        #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
        #conduitApp.Quit()
        self.conduitApplication.Quit()
        return SUCCESS

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='i', out_signature='s')
    def GetDataProviderKey(self, uid):
        key = ""
        if uid in self.UIDs:
            key = self.UIDs[uid].get_key()
        return key

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='as')
    def GetAllDataSources(self):
        self._print("GetAllDataSources")
        #get the dataproviders
        return [i.get_key() for i in self._get_sources()]

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='', out_signature='as')
    def GetAllDataSinks(self):
        self._print("GetAllDataSinks")
        return [i.get_key() for i in self._get_sinks()]

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSource(self, key):
        self._print("GetDataSource %s" % key)
        return self._add_dataprovider(key, self._get_sources())

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='s', out_signature='i')
    def GetDataSink(self, key):
        self._print("GetDataSink %s" % key)
        return self._add_dataprovider(key, self._get_sinks())       

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='s', out_signature='a{ss}')
    def GetDataProviderInformation(self, key):
        self._print("GetDataProviderInformation %s" % key)
        info = {}
        for i in self._get_all_dps():
            if i.get_key() == key:
                #FIXME: Need to call get_icon so that the icon_name/path is loaded
                i.get_icon()

                info["name"] = i.name
                info["description"] = i.description
                info["module_type"] = i.module_type
                info["category"] = i.category.name
                info["in_type"] = i.get_in_type()
                info["out_type"] = i.get_out_type()
                info["classname"] = i.classname
                info["key"] = i.get_key()
                info["enabled"] = str(i.enabled)
                info["UID"] = i.get_UID()
                info["icon_name"] = i.icon_name
                info["icon_path"] = i.icon_path

        return info

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='i', out_signature='as')
    def GetAllCompatibleDataSinks(self, sourceUID):
        """
        Gets all datasinks compatible with the supplied datasource. Compatible 
        is defined as;
        1) Enabled
        2) sink.get_in_type() == source.get_out_type() OR
        3) Conversion is available
        """
        self._print("GetAllCompatibleDataSinks %s" % sourceUID)
        compat = []
        if sourceUID not in self.UIDs:
            return compat

        #look for enabled datasinks
        for s in self._get_sinks():
            if s.enabled == True:
                out = self.UIDs[sourceUID].get_out_type()
                if s.get_in_type() == out:
                    compat.append(s.get_key())
                elif self.type_converter.conversion_exists(out, s.get_in_type()):
                    compat.append(s.get_key())

        return compat

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='i', out_signature='s')
    def GetDataProviderConfiguration(self, uid):
        self._print("GetDataProviderConfiguration %s" % uid)
        xml = ""
        if uid in self.UIDs:
            #create new conduit, populate and add to hashmap
            dataprovider = self.UIDs[uid]
            xml = dataprovider.module.get_configuration_xml()
        return xml

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='is', out_signature='i')
    def SetDataProviderConfiguration(self, uid, xmltext):
        self._print("SetDataProviderConfiguration %s" % uid)
        ok = ERROR
        if uid in self.UIDs:
            #create new conduit, populate and add to hashmap
            dataprovider = self.UIDs[uid]
            dataprovider.module.set_configuration_xml(xmltext)
            ok = SUCCESS
        return ok


    @dbus.service.method(conduit.DBUS_IFACE, in_signature='ii', out_signature='i')
    def BuildConduit(self, sourceUID, sinkUID):
        self._print("BuildConduit %s:%s" % (sourceUID, sinkUID))
        return self._add_conduit(sourceUID, sinkUID)

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='ii', out_signature='i')
    def AddSinkToConduit(self, conduitUID, sinkUID):
        self._print("AddSinkToConduit %s:%s" % (conduitUID, sinkUID))
        uid = ERROR
        if conduitUID in self.UIDs and sinkUID in self.UIDs:
            conduit = self.UIDs[conduitUID]
            conduit.add_dataprovider_to_conduit(self.UIDs[sinkUID])
            uid = conduitUID
        return uid

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='is', out_signature='i')
    def AddDataToSource(self, sourceUID, dataLUID):
        self._print("AddDataToSource %s:%s" % (sourceUID, dataLUID))
        res = ERROR
        if sourceUID in self.UIDs:
            source = self.UIDs[sourceUID]
            if source.module.add(dataLUID):
                res = SUCCESS
        return res

    @dbus.service.method(conduit.DBUS_IFACE, in_signature='ss', out_signature='i')
    def SetSyncPolicy(self, conflictPolicy, deletedPolicy):
        self._print("SetSyncPolicy (conflict:%s deleted:%s)" % (conflictPolicy, deletedPolicy))
        allowedPolicy = ["ask", "replace", "skip"]
        if conflictPolicy not in allowedPolicy:
            return ERROR
        if deletedPolicy not in allowedPolicy:
            return ERROR

        self.sync_manager.set_twoway_policy({
                "conflict"  :   conflictPolicy,
                "deleted"   :   deletedPolicy}
                )
        return SUCCESS


    @dbus.service.method(conduit.DBUS_IFACE, in_signature='i', out_signature='i')
    def Sync(self, conduitUID):
        self._print("Sync %s" % conduitUID)
        if conduitUID in self.UIDs:
            self.sync_manager.sync_conduit(self.UIDs[conduitUID])
            return SUCCESS
        else:
            return ERROR

    @dbus.service.signal(conduit.DBUS_IFACE, signature='s')
    def DataproviderAvailable(self, key):
        self._print("Emmiting DBus signal DataproviderAvailable %s" % key)

    @dbus.service.signal(conduit.DBUS_IFACE, signature='s')
    def DataproviderUnavailable(self, key):
        self._print("Emiting DBus signal DataproviderUnavailable %s" % key)

    @dbus.service.signal(conduit.DBUS_IFACE, signature='s')
    def DataproviderChanged(self, key):
        self._print("Emmiting DBus signal DataproviderChanged %s" % key)

    @dbus.service.signal(conduit.DBUS_IFACE, signature='ib')
    def SyncCompleted(self, conduitUID, error):
        self._print("Emmiting DBus signal SyncCompleted %s (error: %s)" % (conduitUID,error))

    @dbus.service.signal(conduit.DBUS_IFACE, signature='id')
    def SyncProgress(self, conduitUID, progress):
        self._print("Emmiting DBus signal SyncProgress %s %s%%" % (conduitUID,progress*100.0))

    @dbus.service.signal(conduit.DBUS_IFACE, signature='i')
    def Conflict(self, UID):
        self._print("Emmiting DBus signal Conflict")
