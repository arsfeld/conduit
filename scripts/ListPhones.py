import sys
import os.path
import bluetooth
import gammu

# make sure we have conduit folder in path!
my_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(my_path, '..'))
sys.path.insert(0, base_path)

import conduit.Logging as Logging
import conduit.modules.PhoneModule.Data as Data
import conduit.modules.PhoneModule.ScanThreads as ScanThreads
import conduit.modules.PhoneModule.Gammu as Gammu

import logging
log = logging.getLogger("ListPhones")

class FoundPhones:
    def __init__(self):
        self._found = {}

    def found_phone(self, address, name):
        log.info("Phone Manufacturer: %s" % Data.get_vendor_from_bluetooth_address(address))
        if address not in self._found:
            self._found[address] = name

    def lookup_model_information(self):
        for address,name in self._found.items():
            if address in os.environ.get('PHONE_BLACKLIST',"").split(","):
                log.info("Skipping %s, blacklisted" % address)
                continue
            #try all bluetooth connections
            for connection in Data.get_connections_from_bluetooth_address(address):
                log.info("Connecting to %s Using: %s" % (name,connection))
                try:
                    phone = Gammu.GammuPhone(address, connection)
                    phone.sm.Terminate()
                    log.info("\t ---> OK (%s)" % ', '.join(phone.info.values()))
                    break
                except gammu.GSMError, val:
                    log.info("\t ---> Failed")    
    
#discover all the phones
log.info("Searching for Phones")
found = FoundPhones()
discoverer = ScanThreads.DeviceDiscovererFilter(found)
discoverer.find_devices()
discoverer.process_inquiry()

#use gammu to get their manufacturer
found.lookup_model_information()


