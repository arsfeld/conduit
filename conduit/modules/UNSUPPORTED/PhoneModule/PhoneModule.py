import logging
log = logging.getLogger("modules.Phone")

import conduit.dataproviders.File as FileDataProvider
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.utils as Utils
import conduit.Exceptions as Exceptions

try:
    import bluetooth
    MODULES = {
    "PhoneFactory" : { "type": "dataprovider-factory" },
    }
except ImportError:
    MODULES = {}
    log.info("Phone support disabled (bluez/python-bluetooth not installed)")

Utils.dataprovider_add_dir_to_path(__file__, "")
import Gammu

class PhoneFactory(DataProvider.DataProviderFactory):
    """ 
    Looks for phones connected via bluetooth
    """
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)
        self._cats = {}
        self._phones = {}

        #Scan multiple interfaces at once
        self.threads = []
        if Gammu.GAMMU_SUPPORTED:
            self.threads.append(
                Gammu.Bluetooth(self._found_phone_callback)
                #Gammu.Cable
                )
        #else:
        #   phonetooth based scan

    def _found_phone_callback(self, address, name, driver, info):
        #Get/create the named phone category
        if name not in self._cats:
            self._cats[name] = DataProviderCategory.DataProviderCategory(
                                    name,
                                    "phone",
                                    address)    
        category = self._cats[name]

        #create the klass for controlling the phone
        klass = None
        if driver == "test":
            self.emit_added(
                        klass=Test,
                        initargs=(address,),
                        category=category
                        ) 
        elif driver == "bluetooth":
            #check it supports obex file transfer class for file dps
            done = False
            for i in ObexFileDataProvider.SUPPORTED_BLUETOOTH_CLASSES:
                if done: break
                for service in info.get('services',()):
                    if i in service['service-classes']:
                        self.emit_added(
                                klass=ObexFileDataProvider,
                                initargs=(address,),
                                category=category
                                )
                        done = True
                        break             

            #check that gammu found a working connection to the phone
            if info.get('connection',None):
                if Gammu.GAMMU_SUPPORTED:
                    self.emit_added(
                            klass=Gammu.GammuDataProvider,
                            initargs=(address,info['connection']),
                            category=category
                            )
                #else phonetooth based contacts
                #

        else:
            log.warn("No driver supports %s@%s" % (driver,address))

    def probe(self):
        log.info("Starting Scan Threads")
        for t in self.threads:
            t.start()

    def quit(self):
        log.info("Stopping Scan Threads")
        for t in self.threads:
            t.cancel()

class ObexFileDataProvider(FileDataProvider.FolderTwoWay):

    _name_ = "Pictures"
    _configurable_ = False

    #FIXME: Does gnomevfs-obexftp support obexpush also?
    SUPPORTED_BLUETOOTH_CLASSES = (
        bluetooth.OBEX_FILETRANS_CLASS,
    )

    def __init__(self, address, *args):
        FileDataProvider.FolderTwoWay.__init__(
                            self,
                            folder= "obex://[%s]" % address,
                            folderGroupName="Test",
                            includeHidden=False,
                            compareIgnoreMtime=False,
                            followSymlinks=False
                            )
        self.address = address
        #FIXME: In the land of GIO, I think I need to gio-mount this
        #location before I can do anything with it...

    def get_UID(self):
        return self.address

class Test(DataProvider.DataSource):
    _name_ = "Test Phone"
    _description_ = "Test Phone"
    _module_type_ = "source"
    _configurable_ = False
    def __init__(self, address, *args):
        DataProvider.DataSource.__init__(self)

    def get_UID(self):
        return ""

