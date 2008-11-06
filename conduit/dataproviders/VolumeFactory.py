import gobject
import logging
log = logging.getLogger("dataproviders.VolumeFactory")

import conduit
import conduit.dataproviders.HalFactory as HalFactory

class VolumeFactory(HalFactory.HalFactory):
    """  file system based, or
    more technically, that have the volume capability defined in HAL. This 
    usually results in them being mounted as removable volumes.

    We jump through some extra hoops here because there is a race condition
    where we receive notification (the device has capability ("volume"))
    """

    def _wait_for_mount(self, udi, props):
        props.update(self._get_properties(udi))

        if not props.has_key("volume.is_mounted"):
            log.info("Still waiting for HAL to notice: %s" % udi)
            return True
        else:
            try:
                mounted = int(props["volume.is_mounted"])
                if mounted == 1 and self.is_interesting(udi, props):
                    self.item_added(udi, **props)
            except ValueError:
                log.warn("Could not determine if volume was mounted")

            return False

    def _maybe_new(self, device_udi):
        props = self._get_properties(device_udi)
        if "volume" in [str(c) for c in props.get("info.capabilities", [])]:
            #this basically checks if the volume mounting procedure has finished
            if str(props.get("volume.mount_point", "")) == "" or props.has_key("volume.is_mounted") == False:
                log.info("Waiting for HAL to attempt mount")
                gobject.timeout_add(1000, self._wait_for_mount, device_udi, props)
            else:
                if self.is_interesting(device_udi, props):
                    self.item_added(device_udi, **props)

    def probe(self):
        """
        Called after VolumeFactory is initialised to detect already connected volumes
        """
        for device in self.hal.FindDeviceByCapability("volume"):
            self._maybe_new(str(device))

    def get_args(self, udi, **kwargs):
        """
        VolumeFactory passes mount point and udi to dataproviders
        """
        kwargs["mount"] = "file://" + str(kwargs["volume.mount_point"])
        return (kwargs['mount'], udi,)


