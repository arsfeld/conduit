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
import conduit.Module as Module
import gobject

class RemovableDeviceManager(gobject.GObject):
    __gsignals__ = {
        #Fired when the module detects a usb key or ipod added
        "dataprovider-added" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [gobject.TYPE_PYOBJECT])
    }
    def __init__(self, hal):
        gobject.GObject.__init__(self)
        self.hal = hal
        self.hal.connect("ipod-added", self._ipod_added)
        self.hal.connect("usb-added", self._usb_added)

    def _ipod_added(self, hal, udi, mount, name):
        dpw = Module.ModuleWrapper("hal",name,"source", DataProvider.CATEGORY_IPOD,"text","text","classname",None,None,True)
        self.emit("dataprovider-added", dpw)
        

    def _usb_added(self, hal, udi, mount, name):
        dpw = Module.ModuleWrapper("usb",name,"source", DataProvider.CATEGORY_USB,"text","text","classname",None,None,True)
        self.emit("dataprovider-added", dpw)
        

    
    
