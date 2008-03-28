import logging
log = logging.getLogger("modules.Phone")

import thread

import threading
import bluetooth
import time

import conduit

UNKNOWN_VALUE = "Unknown"

class ScanThread(threading.Thread):
    SLEEP_TIME = 20
    SLEEP = 0.1
    def __init__(self):
        threading.Thread.__init__(self)
        self._found = {}
        self._cancelled = False
        self._foundLock = threading.Lock()

    def found_phone(self, address, name):
        #locked because, AIUI, the DeviceDiscover callsback anytime,
        #from another thread
        self._foundLock.acquire()
        if address not in self._found:
            log.info("Thread %s Found Phone: %s" % (thread.get_ident(),address))
            self._found[address] = {"name":name}
        self._foundLock.release()

    def pause_scanning(self):
        i = 0
        while ( i < (self.SLEEP_TIME/self.SLEEP) ) and ( self.is_cancelled() == False ):
            time.sleep(self.SLEEP)
            i += 1

    def is_cancelled(self):
        return conduit.GLOBALS.cancelled or self._cancelled

    def cancel(self):
        self._cancelled = True

class DeviceDiscovererFilter(bluetooth.DeviceDiscoverer):
    def __init__(self, parent):
        bluetooth.DeviceDiscoverer.__init__(self)
        self.parent = parent

    def device_discovered(self, address, device_class, name):
        '''
        Called when device is iscovered, checks device is phone
        '''
        log.info("Bluetooth Device Discovered: %s@%s" % (name,address))
        major_class = ( device_class & 0xf00 ) >> 8
        # We want only devices with phone class
        # See https://www.bluetooth.org/apps/content/?doc_id=49706
        if major_class == 2:
            self.parent.found_phone(address, name)

    def inquiry_complete(self):
        log.debug("Bluetooth Search Complete")


