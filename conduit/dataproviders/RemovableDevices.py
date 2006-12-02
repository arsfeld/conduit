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

import logging
import conduit, conduit.dataproviders
from conduit.DataProvider import DataSource
from conduit.DataProvider import DataSink
from conduit.ModuleWrapper import ModuleWrapper
from Hal import UDI_IDX, MOUNT_IDX, NAME_IDX

import os
import conduit.datatypes.Note as Note

class RemovableDeviceManager(gobject.GObject):
    __gsignals__ = {
        #Fired when the module detects a usb key or ipod added
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT])
    }
    def __init__(self, hal):
        gobject.GObject.__init__(self)

        #dict of detected volumes
        self.UDIs = []
        #Removable device classes
        self.removable_devices = []
        self.hal = hal
        
        #Hal scans in __init__. Get all conected ipods/usb keys
        for device_type, udi, mount, name in self.hal.get_all_ipods():
            self._ipod_added(None,udi,mount,name)

        self.hal.connect("ipod-added", self._ipod_added)
        self.hal.connect("usb-added", self._usb_added)

    def _emit(self, signal, dpw):
        logging.info("Removable Devices: Emitting %s for %s" % (signal, dpw.classname))
        self.emit("dataprovider-added", dpw)

    def _ipod_added(self, hal, udi, mount, name):
        if udi in self.UDIs:
            logging.warn("Removable Devices: UDI %s already used" % udi)
            return
        else:
            #Mark UDI as used
            self.UDIs.append(udi)

            for klass,type in [(IPodNoteSource,"source"), (IPodNoteSink,"sink")]:
                instance = klass(mount, name)
                dpw = ModuleWrapper(
                            instance.name,
                            instance.description,
                            type, 
                            conduit.DataProvider.CATEGORY_IPOD,
                            "note",
                            "note",
                            "%s:%s" % (klass.__name__, mount),       #classname has to be unique
                            "",                                         #filename N/A
                            instance,
                            True)
                self.removable_devices.append(dpw)
                self._emit("dataprovider-added", dpw)

    def _usb_added(self, hal, udi, mount, name):
        pass

    def get_all_modules(self):
        return self.removable_devices

class USBKeySource(DataSource):
    """
    Class will provide a simple way to share files on usb keys between 
    different PCs   
    """
    pass


class IPodNoteSource(DataSource):
    def __init__(self, mountPoint, name):
        DataSource.__init__(self, "%s IPod" % name, "Sync you iPod notes", "tomboy")
        
        self.name = name
        self.mountPoint = mountPoint
        self.notes = []

    def refresh(self):
        DataSource.refresh(self)
        
        mypath = os.path.join(self.mountPoint, 'Notes/')
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
        DataSource.get_num_items(self)
        logging.info(len(self.notes))
        return len(self.notes)

    def get(self, index):
        DataSource.get(self, index)
        return self.notes[index]

class IPodNoteSink(DataSink):
    def __init__(self, mountPoint, name):
        DataSink.__init__(self, "%s IPod" % name, "Sync you iPod notes", "tomboy")
        
        self.name = name
        self.mountPoint = mountPoint
        self.notesPoint = os.path.join(mountPoint, 'Notes/')

    def refresh(self):
        DataSink.refresh(self)
        
    def put(self, note, noteOnTopOf=None):
        DataSink.put(self, note, noteOnTopOf)
	open(os.path.join(self.notesPoint, note.title + ".txt"),'w+').write(note.contents)
        
