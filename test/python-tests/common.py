import sys
import cgitb
import os
import glob
import time
import datetime

# make sure we have conduit folder in path!
my_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(my_path, '..', '..'))
sys.path.insert(0, base_path)

# import main conduit module and datatypes
import conduit
import conduit.Logging as Logging
import conduit.Utils as Utils
import conduit.Module as Module
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization
import conduit.ModuleWrapper as ModuleWrapper
import conduit.Conduit as Conduit
import conduit.SyncSet as SyncSet
import conduit.MappingDB as MappingDB
from conduit.datatypes import File, Note, Setting, Contact, Email, Text, Video, Photo, Audio, Event
from conduit.modules import TestModule

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


def my_except_hook(etype, evalue, etraceback):
    """
    Super verbose unhandled exception information. from
    http://boodebr.org/main/python/tourist/taking-exception
    """
    txt = cgitb.text( (etype,evalue,etraceback) )
    ok("** EXITING on unhandled exception \n%s" % txt,False)
    
#Set a global exception hook for unhandled exceptions
sys.excepthook = my_except_hook
    
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
        
def is_interactive():
    try:    
        return os.environ["CONDUIT_INTERACTIVE"] == "TRUE"
    except KeyError:
        return False
        
def init_gnomevfs_authentication():
    import gnome.ui
    gnome.init(conduit.APPNAME, conduit.APPVERSION)
    gnome.ui.authentication_manager_init()     
    
#Functions to construct new types
def new_file(filename):
    if filename == None:
        f = Utils.new_tempfile(Utils.random_string())
    else:
        files = get_files_from_data_dir(filename)
        f = File.File(URI=files[0])
    uri = f._get_text_uri()
    f.set_UID(uri)
    f.set_open_URI(uri)
    return f

def new_note(title):
    if title == None:
        title = Utils.random_string()
    n = Note.Note(
                title=title,
                contents=Utils.random_string()
                )
    n.set_UID(Utils.random_string())
    n.set_mtime(datetime.datetime(1977,3,23))
    n.set_open_URI(Utils.random_string())
    return n

def new_event(filename):
    if filename == None:
        txt = read_data_file_from_data_dir("1.ical")
    else:
        txt = read_data_file_from_data_dir(filename)
    e = Event.Event()
    e.set_from_ical_string(txt)
    e.set_UID(Utils.random_string())
    e.set_open_URI(Utils.random_string())
    return e

def new_contact(filename):
    if filename == None:
        txt = read_data_file_from_data_dir("1.vcard")
    else:
        txt = read_data_file_from_data_dir(filename)
    c = Contact.Contact()
    c.set_from_vcard_string(txt)
    c.set_UID(Utils.random_string())
    c.set_open_URI(Utils.random_string())
    return c

def new_email(content):
    if content == None:
        content = Utils.random_string()
    e = Email.Email(
                content=content,
                subject=Utils.random_string()
                )
    e.set_UID(Utils.random_string())
    e.set_open_URI(Utils.random_string())
    return e

def new_text(txt):
    if txt == None:
        txt = Utils.random_string()
    t = Text.Text(
                text=txt
                )
    t.set_UID(Utils.random_string())
    t.set_open_URI(Utils.random_string())
    return t

#def new_audio(filename):
#    a = Audio.Audio(
#                URI=filename
#                )                
#    a.set_UID(Utils.random_string())
#    a.set_open_URI(filename)
#    return a

#def new_video(filename):
#    v = Video.Video(
#                URI=filename
#                )                
#    v.set_UID(Utils.random_string())
#    v.set_open_URI(filename)
#    return v

def new_photo(filename):
    if filename == None:
        files = get_files_from_data_dir("*.png")
    else:
        files = get_files_from_data_dir(filename)
    f = Photo.Photo(URI=files[0])
    uri = f._get_text_uri()
    f.set_UID(uri)
    f.set_open_URI(uri)
    return f
    
def new_setting(data):
    if data == None:
        data = Utils.random_string()
    s = Setting.Setting(
                key=Utils.random_string(),
                value=data
                )                
    s.set_UID(Utils.random_string())
    s.set_open_URI(None)
    return s
    
def new_test_datatype(data):
    if data == None:
        data = Utils.random_string(length=1)
    t = TestModule.TestDataType(data)
    return t

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
        wrapper = ModuleWrapper.ModuleWrapper (   
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
                ok("Created new DataProviderClient", newdp != None)
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
        
        abort,error,conflict = self.get_sync_result()
        ok("Sync completed (a:%d e:%d c:%d)" % (abort,error,conflict), True)

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


