import conduit
import conduit.utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.HalFactory as HalFactory
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact
import conduit.Exceptions as Exceptions

import xml.dom.minidom
import vobject

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

TYPETONAMES = {
    SYNC_ITEM_CONTACTS  : "Contacts",
    SYNC_ITEM_CALENDAR  : "Calendar",
    SYNC_ITEM_TASKS     : "Tasks"
}

CHANGE_ADDED        = 1
CHANGE_MODIFIED     = 4
CHANGE_DELETED      = 3

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
                    "windows",
                    udi)

    def get_dataproviders(self, udi, **kwargs):
        return [SynceContactsTwoWay, SynceCalendarTwoWay, SynceTasksTwoWay]

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

    def FlushItemDB(self):
        self.engine.FlushItemDB()

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

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        self.objects = {}
        self.engine.Prefill([TYPETONAMES[self._type_id_]])
        chgs = self.engine.GetRemoteChanges([self._type_id_])
        for guid, chgtype, data in chgs[self._type_id_]:
            uid = array.array('B', guid).tostring()
            blob = array.array('B', data).tostring()
            self.objects[uid] = self._blob_to_data(uid, blob)

        log.info("Got %s objects" % len(self.objects))
        return self.objects.keys()

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self.objects[LUID]

    def put(self, obj, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)
        existing = None
        if LUID != None:
            existing = self.get(LUID)
        if existing != None:
            comp = obj.compare(existing)
            if comp == conduit.datatypes.COMPARISON_EQUAL:
                log.info("objects are equal")
            elif overwrite == True or comp == conduit.datatypes.COMPARISON_NEWER:
                self.update(LUID, obj)
            else:
                raise Exceptions.SynchronizeConflictError(comp, obj, existing)
        else:
            LUID = self.add(obj)
        return self.get(LUID).get_rid()

    def _commit(self, uid, chgtype, blob):
        _uid = array.array('B')
        _uid.fromstring(uid)
        _blob = array.array('B')
        _blob.fromstring(blob)
        self.engine.AddLocalChanges({
            self._type_id_: (
                (_uid, chgtype, _blob),
            )
        })
        # FIXME: This is a HACK to make it easy (ish) to return a RID in put()
        if chgtype != CHANGE_DELETED:
            self.objects[uid] = self._blob_to_data(uid,blob)
        else:
            del self.objects[uid]

    def add(self, obj):
        LUID = Utils.uuid_string()
        self._commit(LUID, CHANGE_ADDED, self._data_to_blob(obj))
        return LUID

    def update(self, LUID, obj):
        self._commit(LUID, CHANGE_MODIFIED, self._data_to_blob(obj))

    def delete(self, LUID):
        DataProvider.TwoWay.delete(self,LUID)
        self._commit(LUID, CHANGE_DELETED, "")

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        #self.engine.AcknowledgeRemoteChanges
        self.engine.Synchronize()
        self.engine.FlushItemDB()

    def _blob_to_data(self, uid, blob):
        #raise NotImplementedError
        d = Note.Note(uid, blob)
        d.set_UID(uid)
        return d

    def _data_to_blob(self, data):
        #raise NotImplementedError
        return data.get_contents()

    def get_UID(self):
        return "synce-%d" % self._type_id_

class SynceContactsTwoWay(SynceTwoWay):
    _name_ = "Contacts"
    _description_ = "Windows Mobile Contacts"
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_CONTACTS
    _configurable_ = False

    def _blob_to_data(self, uid, blob):
        parser = xml.dom.minidom.parseString(blob)
        root = parser.getElementsByTagName("contact")[0]

        c = Contact.Contact()
        c.set_UID(uid)

        def S(node):
            if node and node[0].childNodes:
                return node[0].firstChild.wholeText
            return ""

        for node in root.childNodes:
            if node.nodeName == "FileAs":
                pass
            elif node.nodeName == "FormattedName":
                pass
            elif node.nodeName == "Name":
                family = S(node.getElementsByTagName('LastName'))
                given = S(node.getElementsByTagName('FirstName'))
                try:
                    c.vcard.n
                except:
                    c.vcard.add('n')
                c.vcard.n.value = vobject.vcard.Name(family=family, given=given)
            elif node.nodeName == "Nickname":
                pass
            elif node.nodeName == "Photo":
                pass
            elif node.nodeName == "Categories":
                pass
            elif node.nodeName == "Assistant":
                pass
            elif node.nodeName == "Manager":
                pass
            elif node.nodeName == "Organization":
                pass
            elif node.nodeName == "Spouse":
                pass
            elif node.nodeName == "Telephone":
                pass
            elif node.nodeName == "Title":
                pass
            elif node.nodeName == "Url":
                pass
            elif node.nodeName == "Uid":
                pass
            elif node.nodeName == "Revision":
                pass
            else:
                log.warning("Unhandled node: %s" % node.nodeName)

        return c

    def _data_to_blob(self, data):
        pass

class SynceCalendarTwoWay(SynceTwoWay):
    _name_ = "Calendar"
    _description_ = "Windows Mobile Calendar"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_CALENDAR
    _configurable_ = False

class SynceTasksTwoWay(SynceTwoWay):
    _name_ = "Tasks"
    _description_ = "Windows Mobile Tasks"
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "contact-new"
    _type_id_ = SYNC_ITEM_TASKS
    _configurable_ = False

