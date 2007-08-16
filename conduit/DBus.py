"""
DBus related functionality including the DBus interface and utility 
functions

Copyright: John Stowers, 2006
License: GPLv2
"""
import uuid
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

APPLICATION_DBUS_IFACE="org.conduit.Application"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
UPLOADER_DBUS_IFACE="org.conduit.Upload"
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"

################################################################################
# DBus API Docs
################################################################################
#
# ==== Main Application ====
# Interface	        org.conduit.Application
# Object path       /
#
# Methods:
# BuildConduit(source, sink)
# GetAllDataProviders
# GetDataProvider
# 
# Signals:
# DataproviderAvailable(key)
# DataproviderUnavailable(key)
#
# ==== Conduit ====
# Interface	        org.conduit.Conduit
# Object path       /conduit/{some UUID}
#
# Methods:
# Sync
# Refresh
# 
# Signals:
#
# ==== DataProvider ====
# Interface	        org.conduit.DataProvider
# Object path       /dataprovider/{some UUID}
#
# Methods:
# SetConfigurationXML
# GetConfigurationXML
# 
# Signals:


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
        self.sync_manager = sync_manager
        self.conduit = conduit
        DBusItem.__init__(self, iface=CONDUIT_DBUS_IFACE, path="/conduit/%s" % uuid)

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Sync(self):
        self._print("Sync")
        self.sync_manager.sync_conduit(self.conduit)

    @dbus.service.method(CONDUIT_DBUS_IFACE, in_signature='', out_signature='')
    def Refresh(self):
        self._print("Refresh")
        self.sync_manager.refresh_conduit(self.conduit)

class UploadConduitDBusItem(ConduitDBusItem):
    def __init__(self, sync_manager, conduit, uuid):
        ConduitDBusItem.__init__(self, sync_manager, conduit, uuid)

    @dbus.service.method(UPLOADER_DBUS_IFACE, in_signature='s', out_signature='')
    def AddData(self, data):
        self._print("AddData: %s" % data)
        self.conduit.datasource.module.add(dataLUID)

class DataProviderDBusItem(DBusItem):
    def __init__(self, dataprovider, uuid):
        self.dataprovider = dataprovider
        DBusItem.__init__(self, iface=DATAPROVIDER_DBUS_IFACE, path="/dataprovider/%s" % uuid)

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='', out_signature='s')
    def GetConfigurationXml(self):
        self._print("GetConfigurationXml")
        return self.dataprovider.get_configuration_xml()

    @dbus.service.method(DATAPROVIDER_DBUS_IFACE, in_signature='s', out_signature='')
    def SetConfigurationXml(self, xml):
        self._print("SetConfigurationXml: %s" % xml)
        self.dataprovider.set_configuration_xml(xmltext)

class DBusView(DBusItem):
    def __init__(self, conduitApplication, moduleManager, typeConverter):
        DBusItem.__init__(self, iface=APPLICATION_DBUS_IFACE, path="/")

        self.conduitApplication = conduitApplication
        self.model = None

        #All objects currently exported over the bus
        self.objs = {}

        #setup the module manager
        self.moduleManager = moduleManager
        self.moduleManager.connect("dataprovider-available", self._on_dataprovider_available)
        self.moduleManager.connect("dataprovider-unavailable", self._on_dataprovider_unavailable)

        #type converter and sync manager
        self.type_converter = typeConverter
        self.sync_manager = SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({"conflict":"skip","deleted":"skip"})
        #self.sync_manager.add_syncworker_callbacks(
        #                        self._on_sync_started, 
        #                        self._on_sync_completed, 
        #                        self._on_sync_conflict,
        #                        self._on_sync_progress
        #                        )

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

        i = uuid.uuid4().hex
        new = DataProviderDBusItem(dp, i)
        self.objs[new.get_path()] = new
        return new

    def _add_conduit(self, source=None, sink=None):
        """
        Instantiates a new dataprovider (source or sink), storing it
        appropriately.
        @param key: Key of the DP to create
        @returns: The new DP
        """
        cond = Conduit()
        if source != None:
            if not cond.add_dataprovider(dataprovider_wrapper=source, trySourceFirst=True):
                raise ConduitException("Error adding source to conduit")
        if sink != None:
            if not cond.add_dataprovider(dataprovider_wrapper=sink, trySourceFirst=False):
                raise ConduitException("Error adding source to conduit")

        i = uuid.uuid4().hex
        new = ConduitDBusItem(self.sync_manager, cond, i)
        self.objs[new.get_path()] = new
        return new

    def _on_dataprovider_available(self, loader, dataprovider):
        self.DataproviderAvailable(dataprovider.get_key())

    def _on_dataprovider_unavailable(self, loader, dataprovider):
        self.DataproviderUnavailable(dataprovider.get_key())

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

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='oo', out_signature='o')
    def BuildConduit(self, source, sink):
        self._print("BuildConduit %s --> %s" % (source, sink))
        print self.objs.keys()

        #get the actual dps from their object paths
        try:
            source = self.objs[str(source)].dataprovider
            sink = self.objs[str(sink)].dataprovider
        except KeyError, e:
            raise ConduitException("Could not find dataprovider with key: %s" % e)

        return self._add_conduit(source, sink)

    @dbus.service.method(APPLICATION_DBUS_IFACE, in_signature='', out_signature='')
    def Quit(self):
        if self.conduitApplication != None:
            self.conduitApplication.Quit()

