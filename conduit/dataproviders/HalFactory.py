import gobject
import dbus
import dbus.glib

import conduit.Utils as Utils
import conduit.dataproviders.SimpleFactory as SimpleFactory

class HalFactory(SimpleFactory.SimpleFactory):

    def __init__(self, **kwargs):
        SimpleFactory.SimpleFactory.__init__(self, **kwargs)

        # Connect to system HAL
        self.bus = dbus.SystemBus()
        self.hal_obj = self.bus.get_object("org.freedesktop.Hal", "/org/freedesktop/Hal/Manager")
        self.hal = dbus.Interface(self.hal_obj, "org.freedesktop.Hal.Manager")

        # Hookup signals
        self.hal.connect_to_signal("DeviceAdded", self._device_added)
        self.hal.connect_to_signal("DeviceRemoved", self._device_removed)
        # self.hal.connect_to_signal("NewCapability", self.new_capability)

    def _device_added(self, device_udi, *args):
        props = self._get_properties(device_udi)
        if self.is_interesting(device_udi, props):
            self.item_added(device_udi, **props)

    def _device_removed(self, device_udi):
        self.item_removed(device_udi)

    def _get_properties(self, device):
        try:
            device_dbus_obj = self.bus.get_object("org.freedesktop.Hal" ,device)
            buffer = {}
            for x, y in device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device").items():
                buffer[str(x)] = str(y)
            return buffer
        except:
            return {}

    def probe(self):
        """ Enumerate HAL for any entries of interest """
        devices = self.hal.GetAllDevices()
        for device in self.hal.GetAllDevices():
            device = str(device)
            props = self._get_properties(device)
            if self.is_interesting(device, props):
                 self.item_added(device, **props)

    def get_args(self, udi, **kwargs):
        return (udi,)

