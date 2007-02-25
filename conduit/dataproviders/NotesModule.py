import gtk
from gettext import gettext as _

try:
    import elementtree.ElementTree as ET
except:
    import xml.etree.ElementTree as ET

import dbus


import conduit
from conduit import log,logd,logw
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note
import conduit.datatypes.File as File
import conduit.datatypes.Text as Text
import conduit.Utils as Utils

import os
import os.path
import traceback

TOMBOY_DBUS_PATH = "/org/gnome/Tomboy/RemoteControl"
TOMBOY_DBUS_IFACE = "org.gnome.Tomboy"

MODULES = {
	"TomboyNoteSource" :    { "type": "dataprovider" }
}

class TomboyNoteSource(DataProvider.DataSource):

    _name_ = _("Tomboy Notes")
    _description_ = _("Sync your Tomboy notes")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.notes = []
        self.bus = dbus.SessionBus()
        
    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return True

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.notes = []
        if Utils.dbus_service_available(self.bus,TOMBOY_DBUS_IFACE):
            obj = self.bus.get_object(TOMBOY_DBUS_IFACE, TOMBOY_DBUS_PATH)
            self.remoteTomboy = dbus.Interface(obj, TOMBOY_DBUS_IFACE)
            self.notes = self.remoteTomboy.ListAllNotes()
        else:
            raise Exceptions.RefreshError
                
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        noteURI = self.notes[index]
        n = Note.Note(
                    noteURI,
                    title=self.remoteTomboy.GetNoteTitle(noteURI),
                    modified=self.remoteTomboy.GetNoteChangeDate(noteURI),
                    contents=self.remoteTomboy.GetNoteContents(noteURI)
                    )
        return n
                
    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.notes)

    def finish(self):
        self.notes = None

    def get_UID(self):
        return ""


