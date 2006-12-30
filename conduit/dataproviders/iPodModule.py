"""
Provides a number of dataproviders which are associated with
removable devices such as USB keys.

It also includes classes specific to the ipod. 
This file is not dynamically loaded at runtime in the same
way as the other dataproviders as it needs to be loaded all the time in
order to listen to HAL events

Copyright: John Stowers, 2006
License: GPLv2
"""
import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.Module as Module
from conduit.datatypes import DataType

from gettext import gettext as _

from conduit.DataProvider import DataSource
from conduit.DataProvider import DataSink
from conduit.DataProvider import TwoWay

import os
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact

MODULES = {
        "iPodFactory" :     { "type": "dataprovider-factory" }
}

class iPodFactory(Module.DataProviderFactory):
    def __init__(self, **kwargs):
        Module.DataProviderFactory.__init__(self, **kwargs)

        if kwargs.has_key("hal"):
            self.hal = kwargs["hal"]
            self.hal.connect("ipod-added", self._ipod_added)

    def probe(self):
        """ Probe for iPod's that are already attached """
        for device_type, udi, mount, name in self.hal.get_all_ipods():
            self._ipod_added(None, udi, mount, name)

    def _ipod_added(self, hal, udi, mount, name):
        """ New iPod has been discovered """
        cat = DataProvider.DataProviderCategory(
                    name,
                    "multimedia-player-ipod-video-white",
                    mount)

        for klass in [IPodNoteTwoWay, IPodContactsTwoWay]:
            self.emit_added(
                    klass,           # Dataprovider class
                    (mount,),        # Init args
                    cat)             # Category..

class IPodNoteTwoWay(TwoWay):

    _name_ = _("Notes")
    _description_ = _("Sync your iPod notes")
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        TwoWay.__init__(self)
        
        self.mountPoint = args[0]
        self.notes = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.notes = []

        mypath = os.path.join(self.mountPoint, 'Notes')
        for f in os.listdir(mypath):
            fullpath = os.path.join(mypath, f)
            if os.path.isfile(fullpath):
                title = f
                modified = os.stat(fullpath).st_mtime
                contents = open(fullpath, 'r').read()

                note = Note.Note(title,modified,contents)
                self.notes.append(note)

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.notes)

    def get(self, index):
        TwoWay.get(self, index)
        return self.notes[index]

    def put(self, note, noteOnTopOf=None):
        TwoWay.put(self, note, noteOnTopOf)
        open(os.path.join(self.notesPoint, note.title + ".txt"),'w+').write(note.contents)
        
    def finish(self):
        self.notes = None

class IPodContactsTwoWay(TwoWay):

    _name_ = _("Contacts")
    _description_ = _("Sync your iPod contacts")
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        TwoWay.__init__(self)
        
        self.mountPoint = args[0]
        self.contacts = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.contacts = []

        mypath = os.path.join(self.mountPoint, 'Contacts')
        for f in os.listdir(mypath):
            fullpath = os.path.join(mypath, f)
            if os.path.isfile(fullpath):
                try:
                    contact = Contact.Contact()
                    contact.readVCard(open(fullpath,'r').read())
                    self.contacts.append(contact)
                except:
                    pass

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        TwoWay.get(self, index)
        return self.contacts[index]

    def put(self, contact, contactOnTopOf=None):
        TwoWay.put(self, contact, contactOnTopOf)
        
    def finish(self):
        self.notes = None
