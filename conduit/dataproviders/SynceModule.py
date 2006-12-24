import gtk
from gettext import gettext as _
from elementtree import ElementTree

import logging
import conduit
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

# bit of a hack, will fix itself when SYNCE can be a dynamic provider..
phone_category = conduit.DataProvider.DataProviderCategory(
                        "Phone",
                        "ipod-icon",
                        "Phone")

MODULES = {
        "SynceContactTwoWay" : {
                "name": _("Contacts"),
                "description": _("Source for synchronizing Windows Mobile Phones"),
                "type": "source",
                "category": phone_category,
                "in_type": "text",
                "out_type": "text",
                "icon": "tomboy"
        },
        "SynceCalendarTwoWay" : {
                "name": _("Calendar"),
                "description": _("Source for synchronizing Windows Mobile Phones"),
                "type": "source",
                "category": phone_category,
                "in_type": "text",
                "out_type": "text",
                "icon": "tomboy"
        },
}

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
            if name.lower() = self.obj_type.lower():
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
        logging.info("event fired, my sweet children...")
        self.synchronized_ev.set()

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        return self.objects[index]
                
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.objects)

    def put(self, contact, putContactOnTopOf):
        DataProvider.TwoWay.put(contact, putContactOnTopOf)

    def _temp_create_partnership(self):
        self.synce.CreatePartnership(".conduit", (self.obj_type_id,))

    def _temp_delete_partnership(self):
        #FIXME: this is surely to got a dirty hack!
        # because synce doesn't allow us to sync conduit style we will create a temporary partnership..
        for id, name, host, items in self.synce.GetPartnerships():
            if name == ".conduit":
                self.synce.DeletePartnership(id)

    def finish(self):
        # self.synce.AckChanges
        self._temp_delete_partnership()
        self.objects = None

class SynceContactTwoWay(SynceTwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self, _("Contacts"), _("Sync your Windows Mobile Phones"), "tomboy")
        SynceTwoWay.__init__(self,"contacts",args)

class SynceCalendarTwoWay(SynceTwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self, _("Calendar"), _("Sync your Windows Mobile Phones"), "tomboy")
        SynceTwoWay.__init__(self,"calendar",args)
