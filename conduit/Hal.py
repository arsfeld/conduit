"""
Contains classes for monitoring HAL and sending signals when
various hardware is connected and disconnected.

Parts of this code adapted from GPixPod (GPLv2) (c) Flavio Gargiulo
http://www.gpixpod.org/
Parts of this code adapted from Listen (GPLv2) (c) Mehdi Abaakouk
http://listengnome.free.fr

Copyright: John Stowers, 2006
License: GPLv2
"""

import logging
import conduit
from DBus import dbus_service_available

import gnomevfs
import gobject

import dbus
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

TYPE_IDX = 0
UDI_IDX = 1
MOUNT_IDX = 2
NAME_IDX = 3

IPOD = "ipod"
USB_KEY = "usb"

class HalMonitor(gobject.GObject):
    __gsignals__ = {
        #Fired when an iPod is removed from the system
        "ipod-removed" :    (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_STRING,   #UDI   
                                gobject.TYPE_STRING,    #Mount point
                                gobject.TYPE_STRING)    #Volume label
                            ),
        #Fired when an iPod is added to the system
        "ipod-added" :      (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_STRING,   #UDI
                                gobject.TYPE_STRING,    #Mount point
                                gobject.TYPE_STRING)    #Volume label
                            ),
        #Fired when a USB disk is added to the system
        "usb-removed" :     (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_STRING,   #UDI
                                gobject.TYPE_STRING,    #Mount point
                                gobject.TYPE_STRING)    #Volume label
                            ),

        #Fired when a USB disk is added to the system
        "usb-added" :       (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_STRING,   #UDI
                                gobject.TYPE_STRING,    #Mount point
                                gobject.TYPE_STRING)    #Volume label
                            )
    }
    def __init__(self):
        gobject.GObject.__init__(self)
        self.vol_monitor =  gnomevfs.VolumeMonitor()
        
        self.registered_volumes = []
        self.bus = dbus.SystemBus()
            
        if dbus_service_available(self.bus,'org.freedesktop.Hal'):
            logging.info("HAL Initialized")
            self.vol_monitor.connect("volume-mounted",self._volume_mounted_cb)
            self.vol_monitor.connect("volume-pre-unmount",self._volume_pre_unmounted_cb)
            self.vol_monitor.connect("volume-unmounted",self._volume_unmounted_cb)
        else:
            logging.warn("HAL Could not be Initialized")

    def _emit(self, signal, volume_type, device_udi, mount, name):
        signature = (volume_type, device_udi, mount, name)
        if signature in self.registered_volumes:
            #Remove already detected volumes
            if signal in ["ipod-removed", "usb-removed"]:
                self.registered_volumes.pop(signature)
            else:
                return
        else:
            #Add new volume
            if signal in ["ipod-added", "usb-added"]:
                self.registered_volumes.append(signature)
            else:
                return

        logging.info("Hal: Emitting %s for Volume %s at %s )" % (signal, name, mount))
        self.emit(signal, device_udi, mount, name)

    def _volume_mounted_cb(self,monitor,volume):
        device_udi = volume.get_hal_udi()
        if device_udi :
            properties = self._get_properties(device_udi)
            mount, name = self.get_device_information(properties)
            if self._is_ipod(properties):
                self._emit("ipod-added", IPOD, device_udi, mount, name)
            else:
                self._emit("usb-added", USB_KEY, device_udi, mount, name)
        return True
                
    def _volume_pre_unmounted_cb(self,monitor,volume):
        logging.debug("Pre umount")
        device_udi = volume.get_hal_udi()
        if device_udi :
            pass
        return False
                
    def _volume_unmounted_cb(self,monitor,volume):
        logging.debug("Umount")
        device_udi = volume.get_hal_udi()
        if device_udi :
            properties = self._get_properties(device_udi)
            mount, name = self.get_device_information(properties)
            if self._is_ipod(properties):
                self._emit("ipod-removed", IPOD, device_udi, mount, name)
            else:
                self._emit("usb-removed", USB_KEY, device_udi, mount, name)
        return False

    def _get_properties(self,device_udi):
        try:
            device_dbus_obj = self.bus.get_object("org.freedesktop.Hal" ,device_udi)
            return device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
        except:
            return {}

    def _is_ipod(self,properties):
        if properties.has_key("info.parent") and properties.has_key("info.parent")!="":
            prop2 = self._get_properties(properties["info.parent"])
            if prop2.has_key("storage.model") and prop2["storage.model"]=="iPod":
               return True
        return False  

    def get_device_information(self,properties):
        """
        Returns the mount point and label in a 2-tuple
        """
        if properties.has_key("volume.mount_point"):
            mount = properties["volume.mount_point"]
        else:
            mount = ""
        if properties.has_key("volume.label"):
            label = properties["volume.label"]
        else:
            label = ""

        return (mount, label)

    def scan_hardware(self):
        for volume in self.vol_monitor.get_mounted_volumes():
            device_udi = volume.get_hal_udi()
            if device_udi!=None:
                properties = self._get_properties(device_udi)
                if self._is_ipod(properties):
                    mount, name = self.get_device_information(properties)
                    self._emit("ipod-added", IPOD, device_udi, mount, name)
                else:
                    #FIXME: How do I determine if a volume is removable
                    #(i.e. a USB key) instead of a normal hard disk
                    pass
        #Only run once if run in the idle handler
        return False

    def get_all_ipods(self):
        return [i for i in self.registered_volumes if i[TYPE_IDX] == IPOD]

    def get_all_usb_keys(self):
        return [i for i in self.registered_volumes if i[TYPE_IDX] == USB_KEY]
