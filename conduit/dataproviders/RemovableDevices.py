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
from conduit.ModuleWrapper import ModuleWrapper
from Hal import UDI_IDX, MOUNT_IDX, NAME_IDX

class RemovableDeviceManager(gobject.GObject):
    __gsignals__ = {
        #Fired when the module detects a usb key or ipod added
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT])
    }
    def __init__(self, hal):
        gobject.GObject.__init__(self)
        #Dict of dataproviders indexed by classname
        self.removable_devices = {}
        self.hal = hal
        self.hal.connect("ipod-added", self._ipod_added)
        self.hal.connect("usb-added", self._usb_added)

    def _emit(self, signal, dpw):
        if dpw.classname not in self.removable_devices:
            #Add new device
            logging.info("Removable device %s added" % dpw.classname)
            self.removable_devices[dpw.classname] = dpw
            self.emit("dataprovider-added", dpw)

    def _ipod_added(self, hal, udi, mount, name):
        ipodnote = IPodNoteSource(mount, name)
        dpw = ModuleWrapper(
                    ipodnote.name,
                    ipodnote.description,
                    "source", 
                    conduit.DataProvider.CATEGORY_IPOD,
                    "note",
                    "note",
                    "%s:IPodNoteSource" % mount,    #classname has to be unique
                    "",                             #filename N/A
                    ipodnote,
                    True)
        self._emit("dataprovider-added", dpw)
        #FIXME: self._emit again with a IPodPhoto/Note/Source/Sink/etc
     
    def _usb_added(self, hal, udi, mount, name):
        #dpw = ModuleWrapper("usb",name,"source", CATEGORY_USB,"text","text","classname",None,None,True)
        #self._emit("dataprovider-added", dpw)
        print "USB"

    def load_all_modules(self):
        self.hal.scan_hardware()
        for i in self.hal.get_all_ipods():
            self._ipod_added(None,i[UDI_IDX], i[MOUNT_IDX], i[NAME_IDX])
        for i in self.hal.get_all_usb_keys():
            self._usb_added(None,i[UDI_IDX], i[MOUNT_IDX], i[NAME_IDX])

    def get_all_modules(self):
        return self.removable_devices.values()

class USBKeySource(DataSource):
    """
    Class will provide a simple way to share files on usb keys between 
    different PCs   
    """
    pass


class IPodNoteSource(DataSource):
    def __init__(self, mountPoint, name):
        DataSource.__init__(self, "%s IPod" % name, "Sync you iPod notes", "sticky-notes")
        
        self.name = name
        self.mountPoint = mountPoint
    
