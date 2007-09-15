"""
DBus related functionality including the DBus interface and utility 
functions

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
import conduit.Utils as Utils
import conduit.Synchronization as Synchronization
import conduit.Conduit as Conduit

ERROR = -1
SUCCESS = 0

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
EXPORTER_DBUS_IFACE="org.conduit.Exporter"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

################################################################################
# DBus API Docs
################################################################################
#
# ==== Main Application ====
# Service           org.conduit.Application
# Interface	        org.conduit.Application
# Object path       /
#
# Methods:
# BuildConduit(source, sink)
# BuildExporter(self, sinkKey)
# GetAllDataProviders
# GetDataProvider
# Quit
# 
# Signals:
# DataproviderAvailable(key)
# DataproviderUnavailable(key)
#
# ==== Conduit ====
# Service	        org.conduit.Conduit
# Interface	        org.conduit.Conduit
# Object path       /conduit/{some UUID}
#
# Methods:
# AddDataprovider
# DeleteDataprovider
# Sync
# Refresh
# 
# Signals:
# SyncStarted
# SyncCompleted(aborted, error, conflict)
# SyncConflict
# SyncProgress(progress)
#
# ==== Exporter Conduit ====
# Service	        org.conduit.Conduit
# Interface	        org.conduit.Exporter
# Object path       /conduit/{some UUID}
#
# Methods:
# AddData
# ConfigureSink
# GetSinkInformation
# GetSinkConfiguration
#
# ==== DataProvider ====
# Service	        org.conduit.DataProvider
# Interface	        org.conduit.DataProvider
# Object path       /dataprovider/{some UUID}
#
# Methods:
# IsPending
# SetConfigurationXML
# GetConfigurationXML
# Configure
# GetInformation
# AddData(uri)
# 
# Signals:

#All objects currently exported over the bus
EXPORTED_OBJECTS = {}

class ConduitException(dbus.DBusException):
    _dbus_error_name = 'org.conduit.ConduitException'

class DBusItem(dbus.service.Object):
    def __init__(self, iface, path):
        bus_name = dbus.service.BusName(iface, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, path)

    def get_path(self):
        return self.__dbus_object_path__

    def _print(self, message):
        logd("DBus Message from %s: %s" % (self.get_path(), message))

class ConduitDBusItem(DBusItem):
    def __init__(self, sync_manager, conduit, uuid):
        DBusItem.__init__(self, iface=CONDUIT_DBUS_IFACE, path="/conduit/%s" % uuid)

        self.sync_manager = sync_manager
        self.conduit = conduit
        self.sync_manager.add_syncworker_callbacks(
                                self._on_sync_started, 
                                self._on_sync_completed, 
                                self._on_sync_conflict,
                                self._on_sync_progress
                                )

    def _on_sync_started(self, thread):
        if thread.conduit == self.conduit:
            self.SyncStarted()

    def _on_sync_completed(self, thread, aborted, error, conflict):
        if thread.conduit == self.conduit:
            self.SyncCompleted(bool(aborted), bool(error), bool(conflict))

    def _on_sync_progress(self, thread, progress):
        if thread.conduit == self.conduit:
            self.SyncProgress(float(progress))

    def _on_sync_conflict(self, thread, conflict):
        if thread.conduit == self.conduit:
            self.SyncConflict()   

    #
    # org.conduit.Conduit
    #
    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='ob', out_signature='')
    def AddDataprovider(self, dp, trySource):
        self._print("AddDataprovider: %s" % dp)

        #get the actual dps from their object paths
        try:
            dpw = EXPORTED_OBJECTS[str(dp)].dataprovider
        except KeyError, e:
            raise ConduitException("Could not locate dataprovider: %s" % e)

        if not self.conduit.add_dataprovider(dpw):
            raise ConduitException("Could not add dataprovider: %s" % e)

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='o', out_signature='')
    def DeleteDataprovider(self, dp):
        self._print("DeleteDataprovider: %s" % dp)

        #get the actual dps from their object paths
        try:
            dpw = EXPORTED_OBJECTS[str(dp)].dataprovider
        except KeyError, e:
            raise ConduitException("Could not locate dataprovider: %s" % e)

        if not self.conduit.delete_dataprovider(dpw):
            raise ConduitException("Could not delete dataprovider: %s" % e)

    
    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Sync(self):
        self._print("Sync")
        self.conduit.sync()

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Refresh(self):
        self._print("Refresh")
        self.conduit.refresh()

    @dbus.service.signal(CONDUIT_DBUS_IFACE, signature='')
    def SyncStarted(self):
        self._print("SyncStarted")

    @dbus.service.signal(CONDUIT_DBUS_IFACE, signature='bbb')
    def SyncCompleted(self, aborted, error, conflict):
        self._print("SyncCompleted (abort:%s error:%s conflict:%s)" % (aborted,error,conflict))

    @dbus.service.signal(CONDUIT_DBUS_IFACE, signature='')
    def SyncConflict(self):
        self._print("SyncConflict")

    @dbus.service.signal(CONDUIT_DBUS_IFACE, signature='d')
    def SyncProgress(self, progress):
        self._print("SyncProgress %s%%" % (progress*100.0))

    #
    # org.conduit.Exporter
    #
    @dbus.service.method(EXPORTER_DBUS_IFACE, in_signature='s', out_signature='')
    def ConfigureSink(self, xml):
        self._print("ConfigureSink: %s" % xml)
        if len(self.conduit.datasinks) != 1:
            raise ConduitException("Simple exporter must only have one sink")
        self.conduit.datasinks[0].set_configuration_xml(xml)

    @dbus.service.method(EXPORTER_DBUS_IFACE, in_signature='s', out_signature='')
    def AddData(self, uri):
        self._print("AddData: %s" % uri)
        if self.conduit.datasource == None:
            raise ConduitException("Simple exporter must have a source")

        self.conduit.datasource.module.add(uri)

    @dbus.service.method(EXPORTER_DBUS_IFACE, in_signature='', out_signature='a{ss}')
    def GetSinkInformation(self):
        self._print("GetSinkInformation")
        if len(self.conduit.datasinks) != 1:
            raise ConduitException("Simple exporter must only have one sink")

        #Need to call get_icon so that the icon_name/path is loaded
        self.conduit.datasinks[0].get_icon()

        info = {}
        info["name"] =  self.conduit.datasinks[0].name
        info["description"] =  self.conduit.datasinks[0].description
        info["module_type"] =  self.conduit.datasinks[0].module_type
        info["category"] =  self.conduit.datasinks[0].category.name
        info["in_type"] =  self.conduit.datasinks[0].get_input_type()
        info["out_type"] =  self.conduit.datasinks[0].get_output_type()
        info["classname"] =  self.conduit.datasinks[0].classname
        info["key"] =  self.conduit.datasinks[0].get_key()
        info["enabled"] = str( self.conduit.datasinks[0].enabled)
        info["UID"] =  self.conduit.datasinks[0].get_UID()
        info["icon_name"] =  self.conduit.datasinks[0].icon_name
        info["icon_path"] =  self.conduit.datasinks[0].icon_path
        return info

    @dbus.service.method(EXPORTER_DBUS_IFACE, in_signature='', out_signature='s')
    def GetSinkConfiguration(self):
        self._print("GetSinkConfiguration")
        if len(self.conduit.datasinks) != 1:
            raise ConduitException("Simple exporter must only have one sink")
        return self.conduit.datasinks[0].get_configuration_xml()

class DataProviderDBusItem(DBusItem):
    def __init__(self, dataprovider, uuid):
        DBusItem.__init__(self, iface=DATAPROVIDER_DBUS_IFACE, path="/dataprovider/%s" % uuid)

        self.dataprovider = dataprovider

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='', out_signature='b')
    def IsPending(self):
        self._print("IsPending")
        return self.dataprovider.module == None

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='', out_signature='a{ss}')
    def GetInformation(self):
        self._print("GetInformation")
        #Need to call get_icon so that the icon_name/path is loaded
        self.dataprovider.get_icon()

        info = {}
        info["name"] = self.dataprovider.name
        info["description"] = self.dataprovider.description
        info["module_type"] = self.dataprovider.module_type
        info["category"] = self.dataprovider.category.name
        info["in_type"] = self.dataprovider.get_input_type()
        info["out_type"] = self.dataprovider.get_output_type()
        info["classname"] = self.dataprovider.classname
        info["key"] = self.dataprovider.get_key()
        info["enabled"] = str(self.dataprovider.enabled)
        info["UID"] = self.dataprovider.get_UID()
        info["icon_name"] = self.dataprovider.icon_name
        info["icon_path"] = self.dataprovider.icon_path

        return info

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='', out_signature='s')
    def GetConfigurationXml(self):
        self._print("GetConfigurationXml")
        return self.dataprovider.get_configuration_xml()

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='s', out_signature='')
    def SetConfigurationXml(self, xml):
        self._print("SetConfigurationXml: %s" % xml)
        self.dataprovider.set_configuration_xml(xml)

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='', out_signature='')
    def Configure(self):
        self._print("Configure")       
        self.dataprovider.configure(None)

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='s', out_signature='')
    def AddData(self, uri):
        self._print("AddData: %s" % uri)
        self.dataprovider.module.add(uri)

class DBusView(DBusItem):
    def __init__(self, conduitApplication, moduleManager, typeConverter):
        DBusItem.__init__(self, iface=APPLICATION_DBUS_IFACE, path="/")

        self.conduitApplication = conduitApplication
        
        #We keep a ref of all callers using the interface, and each one gets
        #its own sync set
        self.models = {}

        #setup the module manager
        self.moduleManager = moduleManager
        self.moduleManager.connect("dataprovider-available", self._on_dataprovider_available)
        self.moduleManager.connect("dataprovider-unavailable", self._on_dataprovider_unavailable)

        #type converter and sync manager
        self.type_converter = typeConverter
        self.sync_manager = Synchronization.SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({"conflict":"skip","deleted":"skip"})

    def _get_all_dps(self):
        datasources = self.moduleManager.get_modules_by_type("source")
        datasinks = self.moduleManager.get_modules_by_type("sink")
        twoways = self.moduleManager.get_modules_by_type("twoway")
        return datasources + datasinks + twoways

    def _add_dataprovider(self, key):
        """
        Instantiates a new dataprovider (source or sink), storing it
        appropriately.
        @param key: Key of the DP to create
        @returns: The new DP
        """
        dp = self.moduleManager.get_new_module_instance(key)
        if dp == None:
            raise ConduitException("Could not find dataprovider with key: %s" % key)

        i = Utils.uuid_string()
        new = DataProviderDBusItem(dp, i)
        EXPORTED_OBJECTS[new.get_path()] = new
        return new

    def _add_conduit(self, source=None, sink=None, sender=None):
        """
        Instantiates a new dataprovider (source or sink), storing it
        appropriately.
        @param key: Key of the DP to create
        @returns: The new DP
        """
        if sender == None:
            raise ConduitException("Invalid DBus Caller")

        cond = Conduit.Conduit(self.sync_manager)
        if source != None:
            if not cond.add_dataprovider(dataprovider_wrapper=source, trySourceFirst=True):
                raise ConduitException("Error adding source to conduit")
        if sink != None:
            if not cond.add_dataprovider(dataprovider_wrapper=sink, trySourceFirst=False):
                raise ConduitException("Error adding source to conduit")

        i = Utils.uuid_string()
        new = ConduitDBusItem(self.sync_manager, cond, i)
        EXPORTED_OBJECTS[new.get_path()] = new
        return new

    def _on_dataprovider_available(self, loader, dataprovider):
        self.DataproviderAvailable(dataprovider.get_key())

    def _on_dataprovider_unavailable(self, loader, dataprovider):
        self.DataproviderUnavailable(dataprovider.get_key())

    def set_model(self, model):
        pass

    @dbus.service.signal(APPLICATION_DBUS_IFACE, signature='s')
    def DataproviderAvailable(self, key):
        self._print("Emmiting DBus signal DataproviderAvailable %s" % key)

    @dbus.service.signal(APPLICATION_DBUS_IFACE, signature='s')
    def DataproviderUnavailable(self, key):
        self._print("Emiting DBus signal DataproviderUnavailable %s" % key)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='as')
    def GetAllDataProviders(self):
        self._print("GetAllDataProviders")
        return [i.get_key() for i in self._get_all_dps()]

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='s', out_signature='o')
    def GetDataProvider(self, key):
        self._print("GetDataProvider: %s" % key)
        return self._add_dataprovider(key)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='oo', out_signature='o', sender_keyword='sender')
    def BuildConduit(self, source, sink, sender=None):
        self._print("BuildConduit (sender: %s:) %s --> %s" % (sender, source, sink))

        #get the actual dps from their object paths
        try:
            source = EXPORTED_OBJECTS[str(source)].dataprovider
            sink = EXPORTED_OBJECTS[str(sink)].dataprovider
        except KeyError, e:
            raise ConduitException("Could not find dataprovider with key: %s" % e)

        return self._add_conduit(source, sink, sender)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='s', out_signature='o', sender_keyword='sender')
    def BuildExporter(self, key, sender=None):
        self._print("BuildExporter (sender: %s:) --> %s" % (sender,key))

        source = self._add_dataprovider("FileSource")
        sink = self._add_dataprovider(key)

        return self._add_conduit(source.dataprovider, sink.dataprovider, sender)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Quit(self):
        if self.conduitApplication != None:
            self.conduitApplication.Quit()

