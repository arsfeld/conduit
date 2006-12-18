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
}

class SynceContactTwoWay(DataProvider.TwoWay):
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self, _("Contacts"), _("Source for synchronizing Windows Mobile Phones"), "tomboy")
        self.contacts = None
        self.name_to_id = None

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        
        self.contacts = []
        
        bus = dbus.SessionBus()
        proxy_obj = bus.get_object("org.synce.SyncEngine", "/org/synce/SyncEngine")
        self.synce = dbus.Interface(proxy_obj, "org.synce.SyncEngine")

        self.name_to_id = {}
        for id, name in self.synce.GetItemTypes().items():
            self.name_to_id[name.lower()] = id
        
        # temporary workarounds
        self._temp_delete_partnership()
        self._temp_create_partnership()

        self.synce.StartSync()
       
        items = []
        items.append(self.name_to_id["contacts"])

        chgs = self.synce.GetRemoteChanges(items)
        logging.info(chgs)
        self.contacts.append(str(chgs))
        
    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        return self.contacts[index]
                
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.contacts)

    def put(self, contact, putContactOnTopOf):
        DataProvider.TwoWay.put(contact, putContactOnTopOf)

    def _temp_create_partnership(self):
        self.synce.CreatePartnership(".conduit", (self.name_to_id["contacts"],))

    def _temp_delete_partnership(self):
        #FIXME: this is surely to got a dirty hack!
        # because synce doesn't allow us to sync conduit style we will create a temporary partnership..
        for id, name, host, items in self.synce.GetPartnerships():
            if name == ".conduit":
                self.synce.DeletePartnership(id)

    def finish(self):
        self._temp_delete_partnership()
        self.contacts = None
