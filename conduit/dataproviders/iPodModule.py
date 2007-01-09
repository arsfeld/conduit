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
import conduit.Utils as Utils
from conduit.datatypes import DataType

from gettext import gettext as _

from conduit.DataProvider import DataSource
from conduit.DataProvider import DataSink
from conduit.DataProvider import TwoWay

import os
import conduit.datatypes.Note as Note
import conduit.datatypes.Contact as Contact
import conduit.datatypes.Event as Event

import gnomevfs

MODULES = {
        "iPodFactory" :     { "type": "dataprovider-factory" }
}

def _string_to_unqiue_file(txt, uri, prefix, postfix=''):
    # fixme: gnomevfs is a pain :-(, this function sucks, someone make it nicer? :(
    if gnomevfs.exists(str(os.path.join(uri, prefix + postfix))):
        for i in range(1, 100):
            if False == gnomevfs.exists(str(os.path.join(uri, prefix + str(i) + postfix))):
                break
        uri = str(os.path.join(uri, prefix + str(i) + postfix))
    else:
        uri = str(os.path.join(uri, prefix + postfix))

    temp = Utils.new_tempfile(txt)
    Utils.do_gnomevfs_transfer(temp.URI, gnomevfs.URI(uri), True)

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

        for klass in [IPodNoteTwoWay, IPodContactsTwoWay, IPodCalendarTwoWay]:
            self.emit_added(
                    klass,           # Dataprovider class
                    (mount,udi,),        # Init args
                    cat)             # Category..

class IPodBase(TwoWay):
    def __init__(self, *args):
        TwoWay.__init__(self)
        self.mountPoint = args[0]
        self.uid = args[1]

    def get_UID(self):
        return self.uid

class IPodNoteTwoWay(IPodBase):

    _name_ = _("Notes")
    _description_ = _("Sync your iPod notes")
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
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

    def put(self, note, overwrite, LUIDs=[]):
        TwoWay.put(self, note, overwrite, LUIDs)
        _string_to_unqiue_file(note.contents, self.notePoint, note.tile, '.txt')
        
    def finish(self):
        self.notes = None

class IPodContactsTwoWay(IPodBase):

    _name_ = _("Contacts")
    _description_ = _("Sync your iPod contacts")
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        
        self.dataDir = os.path.join(self.mountPoint, 'Contacts')
        self.contacts = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.contacts = []

        for f in os.listdir(self.dataDir):
            fullpath = os.path.join(self.dataDir, f)
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

    def put(self, contact, overwrite, LUIDs=[]):
        TwoWay.put(self, contact, overwrite, LUIDs)
        _string_to_unqiue_file(str(contact), self.dataDir, 'contact')

    def finish(self):
        self.notes = None

class IPodCalendarTwoWay(IPodBase):

    _name_ = _("Calendar")
    _description_ = _("Sync your iPod calendar")
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "contact-new"

    def __init__(self, *args):
        IPodBase.__init__(self, *args)
        
        self.dataDir = os.path.join(self.mountPoint, 'Calendars')
        self.events = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.events = []

        for f in os.listdir(self.dataDir):
            fullpath = os.path.join(self.dataDir, f)
            if os.path.isfile(fullpath):
                try:
                    event = Event.Event()
                    event.read_string(open(fullpath,'r').read())
                    self.events.append(event)
                except:
                    pass

    def get_num_items(self):
        TwoWay.get_num_items(self)
        return len(self.events)

    def get(self, index):
        TwoWay.get(self, index)
        return self.events[index]

    def put(self, event, overwrite, LUIDs=[]):
        TwoWay.put(self, event, overwrite, LUIDs)
        _string_to_unqiue_file(event.to_string(), self.dataDir, 'event')

    def finish(self):
        self.notes = None

