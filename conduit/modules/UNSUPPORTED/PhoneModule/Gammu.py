#FIXME: Proper license and attribution
#Most code adapted from gammu (GPL2) and phonetooth (GPL2)

import os
import bluetooth
import logging
log = logging.getLogger("modules.Phone")

import conduit.dataproviders.DataProvider as DataProvider
import conduit.utils as Utils
import ScanThreads
import Data

try:
    import gammu
    log.info("Module Information: %s" % Utils.get_module_information(gammu, "__version__"))
    GAMMU_SUPPORTED = True
except ImportError:
    log.info("Gammu based phone support disabled")
    GAMMU_SUPPORTED = False

class GammuPhone:
    """
    Encapsulates the basic connection to a phone using gammu.
    """
    def __init__(self, address, connection, model=''):
        """
        Attempts to connect to the phone at address and connection and
        get all available phone informatin, like the model, manufacturer, etc.
        """
        self.address = address
        self.connection = connection
        self.model = model
        self.isKnownToGammu = False
        self.info = {}
        
        self.sm = gammu.StateMachine()
        self.sm.SetConfig(0, {
            'StartInfo'             :   'no',
            'UseGlobalDebugFile'    :   1,
            'DebugFile'             :   '',
            'SyncTime'              :   'no',
            'Connection'            :   connection,
            'LockDevice'            :   'no',
            'DebugLevel'            :   'nothing',
            'Device'                :   address,
            'Localize'              :   None,
            'Model'                 :   model}
        )
        #dont catch errors thrown here....
        self.sm.Init()
        #if we got here, then we managed a rudimentary connection
        self.info['connection'] = connection
        
        #catch non fatal errors because some phones might not
        #support these fields
        try:
            self.info['manufacturer'] = self.sm.GetManufacturer()
        except gammu.ERR_NOTSUPPORTED, gammu.ERR_NOTIMPLEMENTED: 
            self.info['manufacturer'] = "Unknown"
            
        model = "Unknown"
        try:
            m = self.sm.GetModel()
            if m[0] == '' or m[0] == 'unknown':
                model = m[1]
            else:
                model = m[0]
                self.isKnownToGammu = True
        except gammu.ERR_NOTSUPPORTED, gammu.ERR_NOTIMPLEMENTED:
            model = "Unknown"
        self.info['model'] = model
        
        try:
            self.info['firmware'] = self.sm.GetFirmware()[0]
        except gammu.ERR_NOTSUPPORTED, gammu.ERR_NOTIMPLEMENTED:    
            self.info['firmware'] = "Unknown"
        
class Bluetooth(ScanThreads.ScanThread):
    def __init__(self, foundCallback):
        ScanThreads.ScanThread.__init__(self)
        self.foundCallback = foundCallback
        self.discovery = ScanThreads.DeviceDiscovererFilter(self)
        
        #keep a track of what phones we have seen, so we dont need to find
        #their services over and over again
        # address : name
        self._phones = {}
        
    def lookup_model_information(self, address):
        #try all bluetooth connections
        for connection in Data.get_connections_from_bluetooth_address(address):
            log.info("Connecting to %s Using: %s" % (address,connection))
            try:
                phone = GammuPhone(address, connection)
                phone.sm.Terminate()
                log.info("\t ---> OK (%s)" % ', '.join(phone.info.values()))
                return phone.info
                
            except gammu.GSMError, val:
                log.warn("\t ---> Failed")

        #connection = None means we tried to connect and failed
        return {
            'connection'    :   None
        }
        
    def run(self):
        while self.is_cancelled() == False:
            log.info("Beginning Bluetooth Scan")
            try:
                self.discovery.find_devices()
                self.discovery.process_inquiry()
                for address,info in self._found.items():
                    if address in os.environ.get('PHONE_BLACKLIST',"").split(","):
                        log.info("Skipping %s, blacklisted" % address)
                        continue
                    #Use gammu to lookup the model information. This also tests
                    #if gammu can actually connect to the phone
                    if not info.has_key('connection'):
                        #gammu info
                        info.update(
                                self.lookup_model_information(address)
                                )
                        #services, which may be useful for things like obexftp,
                        #and other dataproviders in the PhoneModule
                        services = bluetooth.find_service(address=address)
                        log.info("Supported services: %s" % ", ".join([i['name'] for i in services]))
                        info['services'] = services
                        
                        self.foundCallback(address,info['name'],"bluetooth",info)
            except bluetooth.BluetoothError:
                log.warn("Error discovering services")

            self.pause_scanning()

    def cancel(self):
        ScanThreads.ScanThread.cancel(self)
        self.discovery.cancel_inquiry()

class Contact:
    def __init__(self, name, phoneNumber):
        self.name = name
        self.phoneNumber = phoneNumber
        
    def __str__(self):
        return self.name + " - " + self.phoneNumber

class GammuDataProvider(DataProvider.DataSource):

    _name_ = "Contacts"
    _module_type_ = "source"
    _in_type_ = "contact"
    _out_type_ = "contact"
    
    #FIXME: What does this mean??
    MAX_EMPTY_GUESS = 5
    MAX_EMPTY_KNOWN = 5

    def __init__(self, address, connection):
        DataProvider.DataSource.__init__(self)
        self.address = address
        self.connection = connection
        #FIXME: Stupid sharp phone obex over bluetooth is broken, so
        #default to at
        self.model = "at"
        self.phone = None

    def get_UID(self):
        return self.address
        
    def _guess_num_items(self):
        return 200

    def _get_first_entry(self):
        '''
        Initiates get next sequence.

        Should be implemented in subclases.
        '''
        raise NotImplementedError

    def _get_next_entry(self, location):
        '''
        Gets next entry.

        Should be implemented in subclases.
        '''
        raise NotImplementedError

    def _get_entry(self, location):
        '''
        Gets entry.

        Should be implemented in subclases.
        '''
        raise NotImplementedError

    def _get_num_items(self):
        '''
        Gets status of entries.

        Should be implemented in subclases.
        '''
        raise NotImplementedError

    def _parse_entry(self):
        '''
        Parses entry.

        Should be implemented in subclases.
        '''
        raise NotImplementedError

    def Send(self):
        '''
        Sends entries to parent.

        Should be implemented in subclases.
        '''
        raise NotImplementedError

    def Run(self):
        '''
        UNFINISHED PORT OF WAMMU's SUBCLASSABLE APPROACH FOR GETTING DATA
        '''
        guess = False
        try:
            total = self._get_num_items()
        except gammu.GSMError, val:
            guess = True
            total = self._guess_num_items()

        remain = total

        data = []

        try:
            start = True
            while remain > 0:
                #if self.canceled:
                #    self.Canceled()
                #    return
                try:
                    if start:
                        value = self._get_first_entry()
                        start = False
                    else:
                        try:
                            loc = value['Location']
                        except TypeError:
                            loc = value[0]['Location']
                        value = self._get_next_entry(loc)
                except gammu.ERR_CORRUPTED:
                    log.warn('While reading, entry on location %d seems to be corrupted, ignoring it!' % loc)
                    continue
                except gammu.ERR_EMPTY:
                    break

                self._parse_entry(value)
                if type(value) == list:
                    for i in range(len(value)):
                        value[i]['Synced'] = True
                else:
                    value['Synced'] = True
                data.append(value)
                remain = remain - 1
        except (gammu.ERR_NOTSUPPORTED, gammu.ERR_NOTIMPLEMENTED):
            location = 1
            empty = 0
            while remain > 0:
                #if self.canceled:
                #    self.Canceled()
                #    return
                try:
                    value = self._get_entry(location)
                    self._parse_entry(value)
                    if type(value) == list:
                        for i in range(len(value)):
                            value[i]['Synced'] = True
                    else:
                        value['Synced'] = True
                    data.append(value)
                    remain = remain - 1
                    # If we didn't know count and reached end, try some more entries
                    if remain == 0 and guess:
                        remain = 20
                        total = total + 20
                    empty = 0
                except gammu.ERR_EMPTY, val:
                    empty = empty + 1
                    # If we didn't know count and saw many empty entries, stop right now
                    if empty >= self.MAX_EMPTY_GUESS and guess:
                        break
                    # If we didn't read anything for long time, we bail out (workaround bad count reported by phone)
                    if empty >= self.MAX_EMPTY_KNOWN and remain < 10:
                        self.ShowError(val[0])
                        remain = 0
                except gammu.ERR_CORRUPTED:
                    log.warn('While reading, entry on location %d seems to be corrupted, ignoring it!' % location)
                    continue
                except gammu.GSMError, val:
                    log.critical(val[0])
                    return
                location = location + 1
        except gammu.ERR_INVALIDLOCATION, val:
            # if we reached end with guess, it is okay
            if not guess:
                log.critical(val[0])
                return
        except gammu.GSMError, val:
            log.critical(val[0])
            return

        #self.Send(data)
        
    def refresh(self):
        if not self.phone:
            self.phone = GammuPhone(self.address, self.connection, self.model)
        log.debug("Connected to phone: %s" % (self.phone.info['model']))
        self.get_all()
            
    def get_all(self):
        #phone = ME, sim = SM
        location = "ME"
        contactList = []
        
        status = self.phone.sm.GetMemoryStatus(Type=location)
        remain = status['Used']
        log.debug("%s contacts on phone" % remain)
        
        start = True
        while remain > 0:
            if start:
                entry = self.phone.sm.GetNextMemory(Start=True, Type=location)
                start = False
            else:
                entry = self.phone.sm.GetNextMemory(Location=entry['Location'], Type=location)
            
            remain = remain - 1
            
            contact = Contact('', '')
            for v in entry['Entries']:
                if v['Type'] == 'Number_General':
                    contact.phoneNumber = v['Value']
                elif v['Type'] == 'Text_Name':
                    contact.name = v['Value']
                
            if len(contact.name) > 0 and len(contact.phoneNumber) > 0:
                print "*"*20,contact
                #contactList.append(contact)

        return contactList


