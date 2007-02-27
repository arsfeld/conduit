import gtk
from gettext import gettext as _

try:
    import elementtree.ElementTree as ET
except:
    import xml.etree.ElementTree as ET


import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File

import os
import os.path
import traceback

import dbus
import dbus.glib

import threading

MODULES = {
    "SynceContactTwoWay" :  { "type": "dataprovider" },
    "SynceCalendarTwoWay" : { "type": "dataprovider" },
    "SynceEmailTwoWay"    : { "type": "dataprovider" },
}

PHONE_CAT = conduit.DataProvider.DataProviderCategory("Phone","media-memory","Phone")

class SynceTwoWay(DataProvider.TwoWay):
    def __init__(self, obj_type, *args):
        self.obj_type = obj_type
        self.objects = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        
        self.objects = []

        # get hold of dbus service        
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object("org.synce.SyncEngine", "/org/synce/SyncEngine")
        self.synce = dbus.Interface(proxy_obj, "org.synce.SyncEngine")

        # get the id for the type of object we want to sync
        for id, name in self.synce.GetItemTypes().items():
            if name.lower() == self.obj_type.lower():
                self.obj_type_id = id

        # temporary workarounds
        self._temp_delete_partnership()
        self._temp_create_partnership()

        self.synce.StartSync()
        self.synce.connect_to_signal("Synchronized", self._synchronized_cb)

        # fixme: this seems to block the signal arriving :-(
        self.synchronized_ev = threading.Event()
        self.synchronized_ev.wait(10)

        # process changes from sync interface
        chgs = self.synce.GetRemoteChanges([self.obj_type_id])
        for luid,changetype,obj in chgs[self.obj_type_id]:
            self.objects.append(str(obj))

    def _synchronized_cb(self):
        log("event fired, my sweet children...")
        self.synchronized_ev.set()

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.objects)

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        return self.objects[index]

    def put(self, obj, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, obj, overwrite, LUID)

        data = str(obj).decode("utf-8")
        self.synce.AddLocalChanges(
            {
                self.obj_type_id : ((str(obj.get_UID()).decode("utf-8"),
                                     obj.change_type,
                                     str(obj)),),
            })

    def finish(self):
        # self.synce.AckChanges
        self._temp_delete_partnership()
        self.objects = None

    def _temp_create_partnership(self):
        self.synce.CreatePartnership(".conduit", (self.obj_type_id,))

    def _temp_delete_partnership(self):
        #FIXME: this is surely to got a dirty hack!
        # because synce doesn't allow us to sync conduit style we will create a temporary partnership..
        for id, name, host, items in self.synce.GetPartnerships():
            if name == ".conduit":
                self.synce.DeletePartnership(id)

class SynceContactTwoWay(SynceTwoWay):
    _name_ = "Contacts"
    _description_ = "Source for synchronizing Windows Mobile Phones"
    _category_ = PHONE_CAT
    _module_type_ = "twoway"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "contact-new"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        SynceTwoWay.__init__(self,"contacts",*args)

class SynceCalendarTwoWay(SynceTwoWay):
    _name_ = "Calendar"
    _description_ = "Source for synchronizing Windows Mobile Phones"
    _category_ = PHONE_CAT
    _module_type_ = "twoway"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "contact-new"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        SynceTwoWay.__init__(self,"calendar",*args)

class SynceEmailTwoWay(SynceTwoWay):
    _name_ = "Email"
    _description_ = "Source for synchronizing Windows Mobile Phones"
    _category_ = PHONE_CAT
    _module_type_ = "twoway"
    _in_type_ = "text"
    _out_type_ = "text"
    _icon_ = "internet-mail"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        SynceTwoWay.__init__(self,"e-mail",*args)

