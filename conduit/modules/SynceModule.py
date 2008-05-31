import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.HalFactory as HalFactory
import conduit.datatypes.Note as Note

import logging
log = logging.getLogger("modules.SynCE")

import os
import os.path
import traceback
import dbus
import dbus.glib
import threading
import gobject
import array

from gettext import gettext as _

SYNC_ITEM_CALENDAR  = 0
SYNC_ITEM_CONTACTS  = 1
SYNC_ITEM_EMAIL     = 2
SYNC_ITEM_FAVORITES = 3
SYNC_ITEM_FILES     = 4
SYNC_ITEM_MEDIA     = 5
SYNC_ITEM_NOTES     = 6
SYNC_ITEM_TASKS     = 7

TYPETONAMES = { SYNC_ITEM_CONTACTS : "Contacts",
                SYNC_ITEM_CALENDAR   : "Calendar",
		SYNC_ITEM_TASKS    : "Tasks"
}

MODULES = {
    "SynceFactory" :        { "type": "dataprovider-factory" },
}

class SynceFactory(HalFactory.HalFactory):

    def is_interesting(self, device, props):
        if props.has_key("sync.plugin") and props["sync.plugin"]=="synce":
            return True
        return False

    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    "Windows Mobile",
                    "media-memory",
                    udi)
    def get_dataproviders(self, udi, **kwargs):
        return [SynceContactTwoWay, SynceCalendarTwoWay]

class SyncEngineWrapper(object):
    """
    Wrap the SyncEngine dbus foo (thinly)
      Make it synchronous and (eventually) borg it so multiple dp's share one connection
    """

    def __init__(self):
        self.engine = None
        self.SyncEvent = threading.Event()
        self.PrefillEvent = threading.Event()

    def _OnSynchronized(self):
        log.info("Synchronize: Got _OnSynchronized")
        self.SyncEvent.set()

    def _OnPrefillComplete(self):
        log.info("Synchronize: Got _OnPrefillComplete")
        self.PrefillEvent.set()

    def Connect(self):
        if not self.engine:
            self.bus = dbus.SessionBus()
            proxy = self.bus.get_object("org.synce.SyncEngine", "/org/synce/SyncEngine")
            self.engine = dbus.Interface(proxy, "org.synce.SyncEngine")
            self.engine.connect_to_signal("Synchronized", lambda: gobject.idle_add(self._OnSynchronized))
            self.engine.connect_to_signal("PrefillComplete", lambda: gobject.idle_add(self._OnPrefillComplete))

    def Prefill(self, items):
        self.PrefillEvent.clear()
        rc = self.engine.PrefillRemote(items)
        if rc == 1:
            self.PrefillEvent.wait(10)
        log.info("Prefill: completed (rc=%d)" % rc)
        return rc

    def Synchronize(self):
        self.SyncEvent.clear()
        self.engine.Synchronize()
        self.SyncEvent.wait(10)
        log.info("Synchronize: completed")

    def GetRemoteChanges(self, type_ids):
        return self.engine.GetRemoteChanges(type_ids)

    def AcknowledgeRemoteChanges(self, acks):
        self.engine.AcknowledgeRemoteChanges(acks)

    def AddLocalChanges(self, chgset):
        self.engine.AddLocalChanges(chgset) 

    def Disconnect(self):
        self.engine = None

class SynceTwoWay(DataProvider.TwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.objects = {}

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.engine = SyncEngineWrapper()    
        self.engine.Connect()
        self.engine.Synchronize()
        self.engine.Prefill([TYPETONAMES[self._type_id_]])
        chgs = self.engine.GetRemoteChanges([self._type_id_])
        for guid, chgtype, data in chgs[self._type_id_]:
            uid = array.array('B', guid).tostring()
            blob = array.array('B', data).tostring()
            self.objects[uid] = Note.Note(uid, blob)
 
    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return [x for x in self.objects.iterkeys()]

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self.objects[LUID]

    def put(self, obj, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)

        data = str(obj).decode("utf-8")
        self.engine.AddLocalChanges(
            {
                self._type_id_ : ((str(obj.get_UID()).decode("utf-8"),
                                     obj.change_type,
                                     str(obj)),),
            })

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        #self.engine.AcknowledgeRemoteChanges
        self.engine.Synchronize()
        self.objects = {}

    def get_UID(self):
        return "synce-%d" % self._type_id_

class SynceContactTwoWay(SynceTwoWay):
    _name_ = "Contacts"
    _description_ = "Source for synchronizing Windows Mobile Phones"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_CONTACTS

class SynceCalendarTwoWay(SynceTwoWay):
    _name_ = "Calendar"
    _description_ = "Source for synchronizing Windows Mobile Phones"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_CALENDAR

