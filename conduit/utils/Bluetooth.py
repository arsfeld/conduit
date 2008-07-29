import threading
import logging
log = logging.getLogger("utils.Bluetooth")

try:
    import bluetooth
    BLUETOOTH_AVAILABLE = True

    class _DeviceDiscovererFilter(bluetooth.DeviceDiscoverer):
        def __init__(self):
            bluetooth.DeviceDiscoverer.__init__(self)
            self._found = {}

        def device_discovered(self, address, device_class, name):
            if not name:
                name = bluetooth.lookup_name(address)
            log.debug("Bluetooth Device Discovered: %s@%s" % (name,address))
            self._found[address] = (name, device_class)

        def inquiry_complete(self):
            log.debug("Bluetooth Search Complete")

        def get_devices(self):
            return self._found

except:
    BLUETOOTH_AVAILABLE = False

    class _DeviceDiscovererFilter:
        def get_devices(self):
            return {}

import conduit.utils.Thread as Thread
import conduit.utils.Singleton as Singleton

def is_computer_class(device_class):
    major_class = ( device_class & 0xf00 ) >> 8
    return major_class == 1

def is_phone_class(device_class):
    major_class = ( device_class & 0xf00 ) >> 8
    return major_class == 2

class BluetoothSearcher(Singleton.Singleton, Thread.PauseCancelThread):
    def __init__(self):
        Thread.PauseCancelThread.__init__(self)
        self._disc = _DeviceDiscovererFilter()
        self._cbs = {}
        self._cblock = threading.Lock()
        
        self.setDaemon(False)
        self.start()

    def watch_for_devices(self, cb, class_check_func=is_phone_class):
        self._cblock.acquire()
        if cb not in self._cbs:
            self._cbs[cb] = class_check_func
        self._cblock.release()

    def call_callbacks(self, address, name, device_class):
        self._cblock.acquire()
        #check if any devices are the class
        for cb, class_check_func in self._cbs.items():
            if class_check_func(device_class):
                #call the registered callback
                cb(address, name)
        self._cblock.release()

    def get_devices(self):
        return self._disc.get_devices()

    def run(self):
        while self.is_cancelled() == False:
            log.debug("Scanning..")

            self._disc.find_devices()
            self._disc.process_inquiry()
            devices = self._disc.get_devices()
            for address in devices:
                self.call_callbacks(address, devices[address][0], devices[address][1])

            self.pause()

