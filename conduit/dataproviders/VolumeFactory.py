import logging
log = logging.getLogger("dataproviders.VolumeFactory")

import conduit
import conduit.dataproviders.HalFactory as HalFactory

class VolumeFactory(HalFactory.HalFactory):
    """ 
    Generic factory for dataproviders that are removable file system based, or
    more technically, that have the volume capability defined in HAL. This 
    usually results in them being mounted as removable volumes.
    """

    def probe(self):
        """
        Called after VolumeFactory is initialised to detect already connected volumes
        """
        for device_udi in self.hal.FindDeviceByCapability("volume"):
            props = self._get_properties(device_udi)
            
            #convert the mountpoint to a string uri because that is what 
            #all the folder dataproviders work on
            if props.get("volume.mount_point"):
                props["mount"] = "file://" + str(props["volume.mount_point"])
                log.debug("Adjusted mount: %s", props["mount"])

            if self.is_interesting(device_udi, props):
                self.item_added(device_udi, **kwargs)

    def get_args(self, udi, **kwargs):
        """ VolumeFactory passes mount point and udi to dataproviders """
        return (kwargs['mount'], udi,)


