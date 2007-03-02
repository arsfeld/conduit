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
import datetime

TOMBOY_DBUS_PATH = "/org/gnome/Tomboy/RemoteControl"
TOMBOY_DBUS_IFACE = "org.gnome.Tomboy"
TOMBOY_MIN_VERSION = (0,5,10)

MODULES = {
	"TomboyNoteTwoWay" :    { "type": "dataprovider" }
}

class TomboyNoteTwoWay(DataProvider.TwoWay):

    _name_ = _("Tomboy Notes")
    _description_ = _("Sync your Tomboy notes")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "twoway"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.notes = []
        self.bus = dbus.SessionBus()

    def _check_tomboy_version(self):
        if Utils.dbus_service_available(self.bus,TOMBOY_DBUS_IFACE):
            obj = self.bus.get_object(TOMBOY_DBUS_IFACE, TOMBOY_DBUS_PATH)
            self.remoteTomboy = dbus.Interface(obj, "org.gnome.Tomboy.RemoteControl")
            version = self.remoteTomboy.Version()
            if version >= TOMBOY_MIN_VERSION:
                log("Using Tomboy Version %s" % version)
                return True
            else:
                logw("Incompatible Tomboy Version %s" % version)
                return False
        else:
            logw("Tomboy DBus interface not found")
            return False

    def initialize(self):
        """
        Loads the tomboy source if the user has used tomboy before
        """
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.notes = []
        if self._check_tomboy_version():
            self.notes = self.remoteTomboy.ListAllNotes()
        else:
            raise Exceptions.RefreshError
                
    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        noteURI = self.notes[index]
        try:
            timestr = self.remoteTomboy.GetNoteChangeDate(noteURI)
            mtime = datetime.datetime.fromtimestamp(int(timestr))
        except:
            logw("Error parsing tomboy note modification time")
            mtime = None

        n = Note.Note(
                    noteURI,
                    title=self.remoteTomboy.GetNoteTitle(noteURI),
                    mtime=mtime,
                    contents=self.remoteTomboy.GetNoteContents(noteURI),
                    raw=self.remoteTomboy.GetNoteXml(noteURI)
                    )
        return n
                
    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.notes)

    def put(self, photo, overwrite, LUID=None):
        """
        Accepts a vfs file. Must be made local.
        I also store a md5 of the photos uri to check for duplicates
        """
        DataProvider.TwoWay.put(self, photo, overwrite, LUID)

        #Check if we have already uploaded the photo
        if LUID != None:
            if LUID in self.notes:            
                if overwrite == True:
                    #replace the note
                    logw("REPLACE NOT IMPLEMENTED")
                    return LUID
                else:
                    #Only replace if newer
                    #comp = photo.compare(flickrFile,True)
                    #logd("Compared %s with %s to check if they are the same (size). Result = %s" % 
                    #        (photo.get_filename(),flickrFile.get_filename(),comp))
                    #if comp != conduit.datatypes.COMPARISON_EQUAL:
                    #    raise Exceptions.SyncronizeConflictError(comp, photo, flickrFile)
                    #else:
                    #    return LUID
                    log("compare")
                    return LUID

        #We havent, or its been deleted so add it
        log("NEW")
        return None

    def finish(self):
        self.notes = None

    def get_UID(self):
        return ""


