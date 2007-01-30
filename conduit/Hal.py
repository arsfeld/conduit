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
import gobject

from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.VolumeMonitor as gnomevfs

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
        self.vol_monitor = gnomevfs.VolumeMonitor()
        
        self.registered_volumes = []
        self.bus = dbus.SystemBus()

        if Utils.dbus_service_available(self.bus,'org.freedesktop.Hal'):
            log("HAL Initialized")
            #Scan hardware first.
            self._scan_hardware()
            #Subsequent detected volumes are added via signals
            self.vol_monitor.connect("volume-mounted",self._volume_mounted_cb)
            self.vol_monitor.connect("volume-pre-unmount",self._volume_pre_unmounted_cb)
            self.vol_monitor.connect("volume-unmounted",self._volume_unmounted_cb)
        else:
            logw("HAL Could not be Initialized")

    def _emit(self, signal, device_udi, mount, name):
        log("Hal: Emitting %s for Volume %s at %s )" % (signal, name, mount))
        self.emit(signal, device_udi, mount, name)

    def _add_volume(self, volume_type, device_udi, mount, name):
        signature = (volume_type, device_udi, mount, name)
        if signature not in self.registered_volumes:
            self.registered_volumes.append(signature)
            if volume_type == IPOD:
                signal = "ipod-added"
            elif volume_type == USB_KEY:
                signal = "usb-added"
            else:
                logw("Hal: Unknown volume type")
                return
            
            #emit the signal
            self._emit(signal, device_udi, mount, name)
        else:
            logw("Hal: Volume allready present. Not adding")

    def _remove_volume(self, volume_type, device_udi, mount, name):
        signature = (volume_type, device_udi, mount, name)
        if signature in self.registered_volumes:
            self.registered_volumes.pop(signature)
            if volume_type == IPOD:
                signal = "ipod-removed"
            elif volume_type == USB_KEY:
                signal = "usb-removed"
            else:
                logw("Hal: Unknown volume type")
                return
            
            #emit the signal
            self._emit(signal, device_udi, mount, name)
        else:
            logw("Hal: Volume doesnt exist. Cannot remove")

    def _volume_mounted_cb(self,monitor,volume):
        device_udi = volume.get_hal_udi()
        if device_udi :
            properties = self._get_properties(device_udi)
            mount, name = self.get_device_information(properties)
            if self._is_ipod(properties):
                self._add_volume(IPOD, device_udi, mount, name)
            else:
                self._add_volume(USB_KEY, device_udi, mount, name)
        return True
                
    def _volume_pre_unmounted_cb(self,monitor,volume):
        logd("Pre umount")
        device_udi = volume.get_hal_udi()
        if device_udi :
            pass
        return False
                
    def _volume_unmounted_cb(self,monitor,volume):
        logd("Umount")
        device_udi = volume.get_hal_udi()
        if device_udi :
            properties = self._get_properties(device_udi)
            mount, name = self.get_device_information(properties)
            if self._is_ipod(properties):
                self._remove_volume(IPOD, device_udi, mount, name)
            else:
                self._remove_volume(USB_KEY, device_udi, mount, name)
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

    def _scan_hardware(self):
        """
        Scans for removable volumes. Adds to the list of registered volumes.
        Does not emit any signals
        """
        for volume in self.vol_monitor.get_mounted_volumes():
            device_udi = volume.get_hal_udi()
            if device_udi!=None:
                properties = self._get_properties(device_udi)
                if self._is_ipod(properties):
                    mount, name = self.get_device_information(properties)
                    signature = (IPOD, device_udi, mount, name)
                    self._add_volume(IPOD, device_udi, mount, name)
                else:
                    #FIXME: How do I determine if a volume is removable
                    #(i.e. a USB key) instead of a normal hard disk
                    #self._add_volume(USB_KEY, device_udi, mount, name)
                    logd("Hal: Skipping non ipod UDI %s" % device_udi)
                    pass
        #Only run once if run in the idle handler
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

    def get_all_ipods(self):
        return [i for i in self.registered_volumes if i[TYPE_IDX] == IPOD]

    def get_all_usb_keys(self):
        return [i for i in self.registered_volumes if i[TYPE_IDX] == USB_KEY]
