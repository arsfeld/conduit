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
import gobject

from gettext import gettext as _

import logging
import conduit, conduit.dataproviders
from conduit.DataProvider import DataSource
from conduit.DataProvider import DataSink
from conduit.DataProvider import TwoWay
from conduit.ModuleWrapper import ModuleWrapper
from Hal import UDI_IDX, MOUNT_IDX, NAME_IDX

import os
import conduit.datatypes.Note as Note

class RemovableDeviceManager(gobject.GObject):
    __gsignals__ = {
        #Fired when the module detects a usb key or ipod added
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_PYOBJECT,      #Wrapper
            gobject.TYPE_PYOBJECT])     #Class
    }
    def __init__(self, hal):
        gobject.GObject.__init__(self)
        self.hal = hal
       
        self.hal.connect("ipod-added", self._ipod_added)
        self.hal.connect("usb-added", self._usb_added)

    def _emit(self, signal, dpw, klass):
        logging.info("Removable Devices: Emitting %s for %s" % (signal, dpw.get_key()))
        self.emit("dataprovider-added", dpw, klass)

    def _ipod_added(self, hal, udi, mount, name, emit=True):
        category = conduit.DataProvider.DataProviderCategory(
                        name,
                        "ipod-icon",
                        mount)

        for klass,type in [(IPodNoteTwoWay,"source")]:
            #FIXME: There is no real need to instantiate this, really some 
            #things should be moved out of MODULES into class properties
            #instance = klass(mount)
            dpw = ModuleWrapper(
                        "Notes",                    #name
                        "Your iPod notes",          #description
                        "tomboy",                   #icon
                        type,                       #type
                        category,                   #category
                        "note",                     #in_type
                        "note",                     #out_type
                        klass.__name__,             #classname has to be unique
                        (mount,),                   #init args
                        )

            if emit == True:
                self._emit("dataprovider-added", dpw, klass)
            else:
                return (dpw, klass)

    def _usb_added(self, hal, udi, mount, name):
        pass

    def get_all_modules(self):
        mods = []
        #Hal scans in __init__. Get all conected ipods/usb keys
        for device_type, udi, mount, name in self.hal.get_all_ipods():
            #Dont emit signals, just return
            mods.append(self._ipod_added(None,udi,mount,name,False))
        return mods

class USBKeySource(DataSource):
    """
    Class will provide a simple way to share files on usb keys between 
    different PCs   
    """
    pass


class IPodNoteTwoWay(TwoWay):
    def __init__(self, *args):
        TwoWay.__init__(self, _("Notes"), _("Sync you iPod notes"), "tomboy")
        
        self.mountPoint = args[0]
        self.notes = None

    def refresh(self):
        TwoWay.refresh(self)
        
        self.notes = []

        mypath = os.path.join(self.mountPoint, 'Notes')
        logging.info(mypath)
        for f in os.listdir(mypath):
            fullpath = os.path.join(mypath, f)
            logging.info(fullpath)
            if os.path.isfile(fullpath):
                title = f
                modified = os.stat(fullpath).st_mtime
                contents = open(fullpath, 'r').read()

                note = Note.Note(title,modified,contents)
                self.notes.append(note)

    def get_num_items(self):
        TwoWay.get_num_items(self)
        logging.info(len(self.notes))
        return len(self.notes)

    def get(self, index):
        TwoWay.get(self, index)
        return self.notes[index]

    def put(self, note, noteOnTopOf=None):
        DataSink.put(self, note, noteOnTopOf)
	open(os.path.join(self.notesPoint, note.title + ".txt"),'w+').write(note.contents)
        
    def finish(self):
        self.notes = None
