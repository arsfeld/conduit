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
# GPixPod - the free and open source way to manage photos on your POD!
# Copyright (C) 2006 Flavio Gargiulo (FLAGAR.com)
#
# This file has been contributed by Abaakouk Mehdi.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

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
            logging.debug("HAL Initialized")
            self.vol_monitor.connect("volume-mounted",self.__volume_mounted_cb)
            self.vol_monitor.connect("volume-pre-unmount",self.__volume_pre_unmounted_cb)
            self.vol_monitor.connect("volume-unmounted",self.__volume_unmounted_cb)
    
    def __volume_mounted_cb(self,monitor,volume):
        device_udi = volume.get_hal_udi()
        if device_udi :
            mount, name = self.get_device_information(device_udi)
            logging.debug("Volume %s Mounted at %s" % (name, mount))
        return True
                
    def __volume_pre_unmounted_cb(self,monitor,volume):
        logging.debug("Pre umount")
        device_udi = volume.get_hal_udi()
        if device_udi :
            pass
        return False
                
    def __volume_unmounted_cb(self,monitor,volume):
        logging.debug("Umount")
        device_udi = volume.get_hal_udi()
        if device_udi :
            pass
        return False

    def _get_properties(self,device_udi):
        try:
            device_dbus_obj = self.bus.get_object("org.freedesktop.Hal" ,device_udi)
            return device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
        except:
            return {}

    def _is_ipod(self,udi):
        prop = self.get_properties(udi)    
        if prop.has_key("info.parent") and prop.has_key("info.parent")!="":
            prop2 = self.get_properties(prop["info.parent"])
            if prop2.has_key("storage.model") and prop2["storage.model"]=="iPod":
               return True
        return False  

    def get_device_information(self,udi):
        """
        Returns the mount point and label in a 2-tuple
        """
        prop = self._get_properties(udi)
        if prop.has_key("volume.mount_point"):
            mount = prop["volume.mount_point"]
        else:
            mount = ""
        if prop.has_key("volume.label"):
            label = prop["volume.label"]
        else:
            label = ""

        return (mount, label)
