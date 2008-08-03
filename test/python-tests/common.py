#coding: utf-8
import sys
import cgitb
import os
import glob
import time
import datetime
import traceback
import ConfigParser
import random

# make sure we have conduit folder in path!
my_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(my_path, '..', '..'))
sys.path.insert(0, base_path)

# import main conduit modules
import conduit
import conduit.Logging as Logging
import conduit.utils as Utils
import conduit.Vfs as Vfs
import conduit.Module as Module
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization
import conduit.ModuleWrapper as ModuleWrapper
import conduit.Conduit as Conduit
import conduit.SyncSet as SyncSet
import conduit.MappingDB as MappingDB
import conduit.Settings as Settings

#import conduit datatypes
from conduit.datatypes import File, Note, Setting, Contact, Email, Text, Video, Photo, Audio, Event, Bookmark
from conduit.modules import TestModule

# set up expected paths & variables 
conduit.IS_INSTALLED =              False
conduit.IS_DEVELOPMENT_VERSION =    True
conduit.SHARED_DATA_DIR =           os.path.join(base_path,"data")
conduit.SHARED_MODULE_DIR =         os.path.join(base_path,"conduit","modules")
conduit.SETTINGS_IMPL =             "GConf"

# override some conduit settings. 
# without a gobject main loop the gtkmozembed browser hangs
conduit.GLOBALS.settings = Settings.Settings(conduit.SETTINGS_IMPL)
conduit.GLOBALS.settings.set_overrides(web_login_browser="system")

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

def skip(msg="no reason given"):
    if msg == "no reason given":
        if not is_online():
            msg = "not online"
        elif not is_interactive():
            msg = "interactive tests disabled"
    print "[SKIPPED] (%s)" % msg
    sys.exit()

def finished():
    print "[FINISHED]"
    sys.exit()

def wait_seconds(s):
    time.sleep(s)

def my_except_hook(etype, evalue, etraceback):
    """
    Super verbose unhandled exception information. from
    http://boodebr.org/main/python/tourist/taking-exception
    """
    txt = cgitb.text( (etype,evalue,etraceback) )
    ok("** EXITING on unhandled exception \n%s" % txt,False)
    
#Set a global exception hook for unhandled exceptions
sys.excepthook = my_except_hook

def get_data_dir():
    return os.path.join(os.path.dirname(__file__),"data")
    
#returns list of files that match the glob in the data dir
def get_files_from_data_dir(glob_str):
    files = []
    for i in glob.glob(os.path.join(get_data_dir(),glob_str)):
        files.append(os.path.abspath(i))
    return files

def read_data_file(name):
    f = open(name,'r')
    txt = f.read()
    f.close()
    return txt

#returns the contents of the file called name in the data dir
def read_data_file_from_data_dir(filename):
    path = os.path.join(get_data_dir(),filename)
    return read_data_file(path)

def init_gnomevfs_authentication():
    import gnome.ui
    gnome.init(conduit.APPNAME, conduit.APPVERSION)
    gnome.ui.authentication_manager_init()     
    
def get_external_resources(typename):
    #Reads the appropriate file (typename.list) and 
    #returns a dict of name:uris beginning with subtypename
    f = os.path.join(get_data_dir(),"%s.list" % typename)
    data = {}
    if os.path.exists(f):
        config = ConfigParser.ConfigParser()
        config.read(f)
        #Default files first
        if is_online():
            for k,v in config.items('DEFAULT'):
                data[k] = v

        #Machine dependent items
        section = Utils.get_user_string()
        if config.has_section(section):
            for k,v in config.items(section):
                data[k] = v
                
    return data

def get_unicode_character():
    #Convenience function to get a unicode character.
    UNICODE_CHARS = ('Ä','á','æ','é','Ë','Ü')
    return UNICODE_CHARS[random.randint(0,len(UNICODE_CHARS)-1)]

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
    
def new_bookmark(data):
    if data == None:
        data = Utils.random_string()
    b = Bookmark.Bookmark(
                    title=data,
                    uri="http://www.%s.com" % Utils.random_string()
                    )
    b.set_UID(Utils.random_string())
    b.set_open_URI(b.get_uri())
    return b

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
        conduit.GLOBALS.moduleManager = self.model
        self.model.load_all(whitelist=None, blacklist=None)
        self.type_converter = TypeConverter.TypeConverter(self.model)
        conduit.GLOBALS.typeManager = self.type_converter
        self.sync_manager = Synchronization.SyncManager(self.type_converter)
        conduit.GLOBALS.syncManager = self.sync_manager

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
                wrapper = self.model.get_module_wrapper_with_instance(dp.get_key())

        ok("Find DataProviderWrapper '%s'" % name, wrapper != None, die)
        return wrapper

    def get_dataprovider_factory(self, className, die=True):
        factory = None
        for f in self.model.dataproviderFactories:
            if f.__class__.__name__ == className:
                factory = f
        ok("Find DataProviderFactory '%s'" % className, factory != None, die)
        return factory

    def wrap_dataprovider(self, dp):
        wrapper = ModuleWrapper.ModuleWrapper(   
                        klass=dp.__class__,
                        initargs=(),
                        category=None
                        )
        wrapper.module = dp
        return wrapper

    def networked_dataprovider(self, dp):
        """
        Dirty evil cludge so we can test networked sync...
        """
        factory = self.get_dataprovider_factory("NetworkServerFactory")
        try:
            server = factory.share_dataprovider(dp)
            ok("Created new DataProviderServer", server != None)
        except:
            ok("Created new DataProviderServer", False)
            

        conduit = Conduit.Conduit(self.sync_manager)
        time.sleep(1)

        factory = self.get_dataprovider_factory("NetworkClientFactory")
        try:
            newdp = factory.dataprovider_create("http://localhost", conduit.uid, server.get_info())
            ok("Created new DataProviderClient", newdp != None)
            return self.wrap_dataprovider( newdp() )
        except:
            ok("Created new DataProviderClient", False)

    def configure(self, source={}, sink={}):
        if len(source) > 0:
            try:
                self.source.module.set_configuration(source)
                ok("Source configured", 
                        self.source.module.is_configured(
                                            isSource=True,
                                            isTwoWay=False))
            except:
                ok("Source configured", False)
        if len(sink) > 0:
            try:
                self.sink.module.set_configuration(sink)
                ok("Sink configured",
                        self.sink.module.is_configured(
                                            isSource=False,
                                            isTwoWay=False))
            except:
                ok("Sink configured", False)

    def get_source(self):
        return self.source
        
    def set_source(self, source):
        self.source = source

    def get_sink(self):
        return self.sink
        
    def set_sink(self, sink):
        self.sink = sink

    def print_mapping_db(self):
        print conduit.GLOBALS.mappingDB.debug()
       
    def do_dataprovider_tests(self, supportsGet, supportsDelete, safeLUID, data, name):
        """
        Tests get(), put(), delete(). Because some dps have a delay between 
        data being put, and it being get()'able use safeLUID for the UID of
        the data to get
        """
        #Test put()
        uid = None
        if data:
            try:
                rid = self.sink.module.put(data, True)
                uid = rid.get_UID()
                ok("Put a %s (%s) " % (name,rid), True)
            except Exception, err:
                traceback.print_exc()
                ok("Put a %s (%s)" % (name,err), False)
            
        #Test get()
        if supportsGet:
            #default to getting the safe file
            if safeLUID != None:
                LUID = safeLUID
                desc = "safe %s" % name
            else:
                LUID = uid
                desc = name
            
            try:
                self.sink.module.refresh()
                f = self.sink.module.get(LUID)
                ok("Get %s %s" % (desc,LUID), f != None)
            except Exception, err:
                traceback.print_exc()
                ok("Get %s (%s)" % (desc,err), False)

        #Test put() to replace
        if data:
            try:
                rid = self.sink.module.put(data, True, uid)
                ok("Update %s (%s)" % (name,rid), True)
            except Exception, err:
                traceback.print_exc()
                ok("Update %s (%s)" % (name,err), False)

        #Test delete() (but only delete data we have put, not the safe data)
        if supportsDelete and uid:
            try:
                self.sink.module.refresh()
                self.sink.module.delete(uid)
                self.sink.module.refresh()
                ok("Delete %s (%s)" % (name,rid), uid not in self.sink.module.get_all())
            except Exception, err:
                traceback.print_exc()
                ok("Delete %s (%s)" % (name,err), False)

    def do_image_dataprovider_tests(self, supportsGet, supportsDelete, safePhotoLUID, ext="png"):
        """
        Tests get(), put(), delete() and Image dataprovider specific
        functions
        """
        #Test get() and image specific friends
        if supportsGet:
            try:
                info = self.sink.module._get_photo_info(safePhotoLUID)
                ok("Got photo info", info != None)
                url = self.sink.module._get_raw_photo_url(info)
                ok("Got photo url (%s)" % url, url != None and Vfs.uri_exists(str(url)))
            except Exception, err:
                traceback.print_exc()
                ok("Got photo info/url (%s)" % err, False)
        
        data = Photo.Photo(URI="http://files.conduit-project.org/screenshot.%s" % ext)
        self.do_dataprovider_tests(
                    supportsGet,
                    supportsDelete,
                    safePhotoLUID, 
                    data,
                    "photo"
                    )
        
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
                ok("Source configured",
                        self.source.module.is_configured(
                                            isSource=True,
                                            isTwoWay=self.conduit.is_two_way()))
            except:
                ok("Source configured", False)
        if len(sink) > 0:
            for i in xrange(0, len(self.conduit.datasinks)):
                try:
                    self.get_sink(i).module.set_configuration(sink)
                    ok("Sink %s configured" % i,
                            self.get_sink(i).module.is_configured(
                                            isSource=False,
                                            isTwoWay=self.conduit.is_two_way()))
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
        for policyName, policyValue in policy.items():
            self.conduit.set_policy(policyName, policyValue)

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


