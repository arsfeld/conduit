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
import gnomevfs
import dbus
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

from conduit import log,logd,logw

def __init__():
    MonitorInstance = None

def VolumeMonitor():
    if not MonitorInstance:
        MonitorInstance = gnomevfs.VolumeMonitor()
    return MonitorInstance

class VolumeMonitor:
    """ Wraps the actual VolumeMonitor class so only one is ever instanced """

    # storage for the instance reference
    __instance = None

    def __init__(self):
        """ Create singleton instance """
        log("VolumeMonitor.__init__")
        # Check whether we already have an instance
        if VolumeMonitor.__instance is None:
            log("VolumeMonitor.__init__.instancing")
            # Create and remember instance
            VolumeMonitor.__instance = gnomevfs.VolumeMonitor()

        # Store instance reference as the only member in the handle
        self.__dict__['_Singleton__instance'] = VolumeMonitor.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
