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
import conduit.DBus as DBus

import gnomevfs
import gobject

try: 
    import dbus
    if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
        import dbus.glib
except: 
    dbus_imported = False
else: 
    dbus_imported=True

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
        
        self.registered_volume = []
        if dbus_imported:
            try:
                self.bus = dbus.SystemBus()
            except:
                self.bus=None
            
        if dbus_imported and self.bus and DBus.dbus_service_available(self.bus,'org.freedesktop.Hal'):
            logging.info("HAL Initialized")
            self.vol_monitor.connect("volume-mounted",self._volume_mounted_cb)
            self.vol_monitor.connect("volume-pre-unmount",self._volume_pre_unmounted_cb)
            self.vol_monitor.connect("volume-unmounted",self._volume_unmounted_cb)
    
        #Scan all the allready plugged in devices at startup on an idle handler
        #cause it takes some time
        gobject.idle_add(self._scan_hardware)

    def _volume_mounted_cb(self,monitor,volume):
        device_udi = volume.get_hal_udi()
        if device_udi :
            properties = self._get_properties(device_udi)
            mount, name = self.get_device_information(properties)
            if self._is_ipod(properties):
                logging.debug("Ipod %s Mounted at %s)" % (name, mount))
                self.emit("ipod-added", device_udi, mount, name)
            else:
                logging.debug("Volume %s Mounted at %s)" % (name, mount))
                self.emit("usb-added", device_udi, mount, name)
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
                logging.debug("Ipod %s Mounted at %s)" % (name, mount))
                self.emit("ipod-removed", device_udi, mount, name)
            else:
                logging.debug("Volume %s Mounted at %s)" % (name, mount))
                self.emit("usb-removed", device_udi, mount, name)
        return False

    def _scan_hardware(self):
        for volume in self.vol_monitor.get_mounted_volumes():
            device_udi = volume.get_hal_udi()
            if device_udi!=None:
                properties = self._get_properties(device_udi)
                if self._is_ipod(properties):
                    mount, name = self.get_device_information(properties)
                    self.emit("ipod-added", device_udi, mount, name)
                else:
                    #FIXME: How do I determine if a volume is removable
                    #(i.e. a USB key) instead of a normal hard disk
                    pass
        #Only run once in the idle handler
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
