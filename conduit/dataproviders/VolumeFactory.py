
import logging
log = logging.getLogger("dataproviders.SimpleFactory")

import conduit
import conduit.dataproviders.SimpleFactory as SimpleFactory
import conduit.Utils as Utils

import gnomevfs
import dbus

class VolumeFactory(SimpleFactory.SimpleFactory):
    """ 
    Generic factory for dataproviders that are removable file system based
    """

    def __init__(self, **kwargs):
        SimpleFactory.SimpleFactory.__init__(self, **kwargs)

        self.vol_monitor = gnomevfs.VolumeMonitor()
        self.bus = dbus.SystemBus()

        if Utils.dbus_service_available(self.bus,'org.freedesktop.Hal'):
            log.info("HAL Initialized")
            self.vol_monitor.connect("volume-mounted",self._volume_mounted_cb)
            self.vol_monitor.connect("volume-unmounted",self._volume_unmounted_cb)
        else:
            log.warn("HAL Could not be Initialized")

    def _volume_mounted_cb(self, monitor, volume):
        log.debug("Volume mounted")
        device_udi = volume.get_hal_udi()
        if device_udi :
            props = self._get_properties(device_udi)
            if self.is_interesting(device_udi, props):
                mount, label = self._get_device_info(props)
                kwargs = { "mount": mount, "label": label }
                self.item_added(device_udi, **kwargs)
        return True

    def _volume_unmounted_cb(self, monitor, volume):
        log.debug("Volume Umounted")
        device_udi = volume.get_hal_udi()
        if device_udi :
            if self.is_interesting(device_udi, self._get_properties(device_udi)):
                self.item_removed(device_udi)
        return False

    def probe(self):
        """
        Called after VolumeFactory is initialised to detect already connected volumes
        """
        for volume in self.vol_monitor.get_mounted_volumes():
            device_udi = volume.get_hal_udi()
            if device_udi != None:
                props = self._get_properties(device_udi)
                if self.is_interesting(device_udi, props):
                    mount, label = self._get_device_info(props)
                    kwargs = { "mount": mount, "label": label }
                    print device_udi, kwargs
                    self.item_added(device_udi, **kwargs)

    def _get_properties(self, device_udi):
        try:
            device_dbus_obj = self.bus.get_object("org.freedesktop.Hal" ,device_udi)
            return device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
        except:
            return {}

    def _get_device_info(self, properties):
        """
        Returns the mount point and label in a 2-tuple
        """
        if properties.has_key("volume.mount_point"):
            mount = str(properties["volume.mount_point"])
        else:
            mount = ""
        if properties.has_key("volume.label"):
            label = str(properties["volume.label"])
        else:
            label = ""

        return (mount, label)

    def get_args(self, udi, **kwargs):
        """ VolumeFactory passes mount point and udi to dataproviders """
        return (kwargs['mount'], udi,)

    def is_interesting(self, udi, properties):
        raise NotImplementedError
