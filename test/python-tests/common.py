import sys
import os
import glob
import time
import datetime

# make sure we have conduit folder in path!
my_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(my_path, '..', '..'))
sys.path.insert(0, base_path)

# import main conduit module
import conduit
#enable logging
import conduit.Logging

# import code used by SimpleSync tests
import conduit.Utils as Utils
import conduit.Module as Module
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization
from conduit.ModuleWrapper import ModuleWrapper
import conduit.Conduit as Conduit
import conduit.Exceptions as Exceptions
import conduit.SyncSet as SyncSet
import conduit.MappingDB as MappingDB

# set up expected paths & variables 
conduit.IS_INSTALLED =          False
conduit.SHARED_DATA_DIR =       os.path.join(base_path,"data")
conduit.SHARED_MODULE_DIR =     os.path.join(base_path,"conduit","modules")

def ok(message, code, die=True):
    if type(code) == int:
        if code == -1:
            print "[FAIL] %s" % message
            if die:
                sys.exit()
            return False
        else:
            print "[PASS] %s" % message
            return True
    elif type(code) == bool:
        if code == False:
            print "[FAIL] %s" % message
            if die:
                sys.exit()
            return False
        else:
            print "[PASS] %s" % message
            return True

def skip():
    print "[SKIPPED]"
    sys.exit()

def finished():
    print "[FINISHED]"
    sys.exit()

#returns list of files that match the glob in the data dir
def get_files_from_data_dir(glob_str):
    files = []
    for i in glob.glob(os.path.join(os.path.dirname(__file__),"data",glob_str)):
        files.append(os.path.abspath(i))
    return files

def read_data_file(name):
    f = open(name,'r')
    txt = f.read()
    f.close()
    return txt

#returns the contents of the file called name in the data dir
def read_data_file_from_data_dir(filename):
    path = os.path.join(os.path.dirname(__file__),"data",filename)
    return read_data_file(path)

def is_online():
    try:    
        return os.environ["CONDUIT_ONLINE"] == "TRUE"
    except KeyError:
        return False

def init_gnomevfs_authentication():
    import gnome.ui
    gnome.init(conduit.APPNAME, conduit.APPVERSION)
    gnome.ui.authentication_manager_init()     
    
#Functions to construct new types
def new_file(filename):
    if filename == None:
        txt = Utils.random_string()
    else:
        files = get_files_from_data_dir(filename)
        txt = read_data_file(files[0])
    f = Utils.new_tempfile(txt)
    f.set_UID(Utils.random_string())
    f.set_open_URI(Utils.random_string())
    return f

def new_note(filename):
    n = conduit.datatypes.Note.Note(
                title=Utils.random_string(),
                contents=Utils.random_string()
                )
    n.set_UID(Utils.random_string())
    n.set_mtime(datetime.datetime(1977,3,23))
    n.set_open_URI(Utils.random_string())
    return n

def new_event(filename):
    icals = get_files_from_data_dir(filename)
    e = conduit.datatypes.Event.Event(
                URI=Utils.random_string()
                )
    e.set_from_ical_string( read_data_file(icals[0]) )
    e.set_UID(Utils.random_string())
    e.set_open_URI(Utils.random_string())
    return e

def new_contact(filename):
    vcards = get_files_from_data_dir(filename)
    c = conduit.datatypes.Contact.Contact(
                URI=Utils.random_string()
                )
    c.set_from_vcard_string( read_data_file(vcards[0]) )
    c.set_UID(Utils.random_string())
    c.set_open_URI(Utils.random_string())
    return c

def new_email(filename):
    e = conduit.datatypes.Email.Email(
                content=Utils.random_string(),
                subject=Utils.random_string()
                )
    e.set_UID(Utils.random_string())
    e.set_open_URI(Utils.random_string())
    return e

def new_text(data):
    t = conduit.datatypes.Text.Text(
                text=data
                )
    t.set_UID(Utils.random_string())
    t.set_open_URI(Utils.random_string())
    return t

def new_audio(filename):
    a = conduit.datatypes.Audio.Audio(
                URI=filename
                )                
    a.set_UID(Utils.random_string())
    a.set_open_URI(filename)
    return a

def new_video(filename):
    v = conduit.datatypes.Video.Video(
                URI=filename
                )                
    v.set_UID(Utils.random_string())
    v.set_open_URI(filename)
    return v

def new_photo(filename):
    p = conduit.datatypes.Photo.Photo(
                URI=filename
                )                
    p.set_UID(Utils.random_string())
    p.set_open_URI(filename)
    return p

class SimpleTest(object):
    """
    Helper class to make testing dataproviders easy as possible
    """
    def __init__(self, sourceName=None, sinkName=None):
        #Set up our own mapping DB so we dont pollute the global one
        dbFile = os.path.join(os.environ['TEST_DIRECTORY'],Utils.random_string()+".db")
        conduit.GLOBALS.mappingDB = MappingDB.MappingDB(dbFile)

        #Dynamically load all datasources, datasinks and converters
        dirs_to_search =    [
                            conduit.SHARED_MODULE_DIR,
                            os.path.join(conduit.USER_DIR, "modules")
                            ]

        self.model = Module.ModuleManager(dirs_to_search)
        self.model.load_all()
        self.type_converter = TypeConverter.TypeConverter(self.model)
        self.sync_manager = Synchronization.SyncManager(self.type_converter)

        ok("Environment ready", self.model != None and self.type_converter != None and self.sync_manager != None)

        self.source = None
        if sourceName != None:
            self.source = self.get_dataprovider(sourceName)

        self.sink = None
        if sinkName != None:
            self.sink = self.get_dataprovider(sinkName)

        self.sync_set = SyncSet.SyncSet(
                        moduleManager=self.model,
                        syncManager=self.sync_manager
                        )

    def get_dataprovider(self, name, die=True):
        """
        Return a DP identified by a given name
        """
        wrapper = None
        for dp in self.model.get_all_modules():
            if dp.classname == name:
                wrapper = self.model.get_new_module_instance(dp.get_key())

        ok("Find wrapper '%s'" % name, wrapper != None, die)
        return wrapper

    def wrap_dataprovider(self, dp):
        wrapper = ModuleWrapper (   
                    getattr(dp, "_name_", ""),
                    getattr(dp, "_description_", ""),
                    getattr(dp, "_icon_", ""),
                    getattr(dp, "_module_type_", ""),
                    None,
                    getattr(dp, "_in_type_", ""),
                    getattr(dp, "_out_type_", ""),
                    dp.__class__.__name__,     #classname
                    tuple([]),
                    dp,
                    True
                    )

        return wrapper

    def networked_dataprovider(self, dp):
        """
        Dirty evil cludge so we can test networked sync...
        """
        found = False

        conduit = Conduit.Conduit(self.sync_manager)

        #fixme: need cleaner way to get networked factory..
        for i in range(0, len(self.model.dataproviderFactories)):
            factory = self.model.dataproviderFactories[i]
            if str(factory).find("NetworkServerFactory") != -1:
                found = True
                factory.share_dataprovider(conduit, dp)
                break

        if found == False:
            return None

        time.sleep(1)

        for i in range(0, len(self.model.dataproviderFactories)):
            factory = self.model.dataproviderFactories[i]
            if str(factory).find("NetworkClientFactory") != -1:
                newdp = factory.dataprovider_create("http://localhost:3400/", conduit.uid, None)
                ok("Created new ClientDataProvider", newdp != None)
                return self.wrap_dataprovider( newdp() )

    def configure(self, source={}, sink={}):
        if len(source) > 0:
            try:
                self.source.module.set_configuration(source)
                ok("Source configured", True)
            except:
                ok("Source configured", False)
        if len(sink) > 0:
            try:
                self.sink.module.set_configuration(sink)
                ok("Sink configured", True)
            except:
                ok("Sink configured", False)

    def get_source(self):
        return self.source

    def get_sink(self):
        return self.sink

    def print_mapping_db(self):
        print conduit.GLOBALS.mappingDB.debug()

class SimpleSyncTest(SimpleTest):
    """
    Helper class to make setting up test-pairs as easy as possible
    """

    def __init__(self):
        SimpleTest.__init__(self)

    def prepare(self, source, sink):
        self.source = source
        ok("Source ready", self.source != None)

        ok("Sink ready", sink != None)

        self.conduit = Conduit.Conduit(self.sync_manager)
        ok("Conduit created", self.conduit != None)

        self.conduit.add_dataprovider(self.source)
        self.conduit.add_dataprovider(sink)

    def add_extra_sink(self, sink):
        if sink != None:
            i = self.conduit.add_dataprovider(sink)
            ok("Added extra sink", i)

    def configure(self, source={}, sink={}):
        if len(source) > 0:
            try:
                self.source.module.set_configuration(source)
                ok("Source configured", True)
            except:
                ok("Source configured", False)
        if len(sink) > 0:
            for i in xrange(0, len(self.conduit.datasinks)):
                try:
                    self.get_sink(i).module.set_configuration(sink)
                    ok("Sink %s configured" % i, True)
                except:
                    ok("Sink %s configured" % i, False)

    def refresh(self):
        #refresh conduit
        self.conduit.refresh(block=True)

        aborted = self.sync_aborted() 
        ok("Refresh completed", aborted != True)

        return self.get_source_count(), self.get_sink_count()

    def sync(self, debug=True):
        #sync conduit
        self.conduit.sync(block=True)

        if debug:
            print conduit.GLOBALS.mappingDB.debug()

        return (self.get_source_count(), self.get_sink_count())

    def get_sink(self, index=0):
        #support multiple sinks
        return self.conduit.datasinks[index]

    def get_source_count(self):
        try:
            self.source.module.refresh()
        except Exception: pass

        return self.source.module.get_num_items()

    def get_sink_count(self):
        try:
            self.get_sink().module.refresh()
        except Exception: pass

        #might not apply if the sink is not two way
        try:
            count = self.get_sink().module.get_num_items()
        except AttributeError:
            count = 0
        return count

    def set_two_way_sync(self, val):
        if val:
            self.conduit.enable_two_way_sync()
        else:
            self.conduit.disable_two_way_sync()

    def set_two_way_policy(self, policy):
        self.sync_manager.set_twoway_policy(policy)

    def get_two_way_sync(self):
        return self.conduit.is_two_way()

    def can_two_way(self):
        return self.conduit.can_do_two_way_sync()

    def set_slow_sync(self, val):
        if val:
            self.conduit.enable_slow_sync()
        else:
            self.conduit.disable_slow_sync()

    def get_slow_sync(self):
        return self.conduit.do_slow_sync()

    def sync_aborted(self):
        return self.sync_manager.did_sync_abort(self.conduit) 

    def sync_errored(self):
        return self.sync_manager.did_sync_error(self.conduit) 

    def sync_conflicted(self):
        return self.sync_manager.did_sync_conflict(self.conduit)
        
    def get_sync_result(self):
        return self.sync_aborted(), self.sync_errored(), self.sync_conflicted()


