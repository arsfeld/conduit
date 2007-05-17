import sys
import os
import glob
import time

# make sure we have conduit folder in path!
my_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(my_path, '..', '..'))
sys.path.insert(0, base_path)

# import main conduit module
import conduit

# import code used by SimpleSync tests
import conduit.Utils as Utils
import conduit.Module as Module
import conduit.TypeConverter as TypeConverter
import conduit.Synchronization as Synchronization
from conduit.ModuleWrapper import ModuleWrapper
import conduit.Conduit as Conduit

# set up expected paths & variables 
conduit.IS_INSTALLED =          False
conduit.SHARED_DATA_DIR =       os.path.join(base_path,"data")
conduit.GLADE_FILE =            os.path.join(base_path,"data","conduit.glade")
conduit.SHARED_MODULE_DIR =     os.path.join(base_path,"conduit")
conduit.EXTRA_LIB_DIR =         os.path.join(base_path,"contrib")

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

#returns list of files that match the glob in the data dir
def get_files_from_data_dir(glob_str):
    files = []
    for i in glob.glob(os.path.join(os.path.dirname(__file__),"data",glob_str)):
        files.append(os.path.abspath(i))
    return files

#returns the contents of the file called name in the data dir
def read_data_file(name):
    f = open(name,'r')
    txt = f.read()
    f.close()
    return txt

def is_online():
    try:    
        return os.environ["CONDUIT_ONLINE"] == "TRUE"
    except KeyError:
        return False

class SimpleSyncTest(object):
    """
    Helper class to make setting up test-pairs as easy as possible
    """

    def __init__(self):
        #Set up our own mapping DB so we dont pollute the global one
        conduit.mappingDB.open_db(os.path.join(os.environ['TEST_DIRECTORY'],Utils.random_string()+".db"))

        #Dynamically load all datasources, datasinks and converters
        dirs_to_search =    [
                            os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                            os.path.join(conduit.USER_DIR, "modules")
                            ]

        self.model = Module.ModuleManager(dirs_to_search)
        self.type_converter = TypeConverter.TypeConverter(self.model)
        self.sync_manager = Synchronization.SyncManager(self.type_converter)

        ok("Environment ready", self.model != None and self.type_converter != None and self.sync_manager != None)

    def print_mapping_db(self):
        print conduit.mappingDB.debug()

    def prepare(self, source, sink):
        self.source = source
        ok("Source ready", self.source != None)

        self.sink = sink
        ok("Sink ready", self.sink != None)

        self.conduit = Conduit.Conduit()
        ok("Conduit created", self.conduit != None)

        self.conduit.add_dataprovider_to_conduit(self.source)
        self.conduit.add_dataprovider_to_conduit(self.sink)

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

    def refresh(self):
        #refresh conduit
        self.sync_manager.refresh_conduit(self.conduit)
        self.sync_manager.join_all()

        aborted = self.sync_manager.sync_aborted(self.conduit) 
        ok("Refresh completed", aborted != True)

        return self.source.module.get_num_items(), self.sink.module.get_num_items()

    def sync(self):
        #sync conduit
        self.sync_manager.sync_conduit(self.conduit)
        # wait for sync to finish
        self.sync_manager.join_all()

        #print conduit.mappingDB.debug()
        aborted = self.sync_manager.sync_aborted(self.conduit) 
        ok("Sync completed", aborted != True)

        time.sleep(1)

        return (self.get_source_count(), self.get_sink_count())

    def get_source_count(self):
        self.source.module.refresh()
        return self.source.module.get_num_items()

    def get_sink_count(self):
        self.sink.module.refresh()
        return self.sink.module.get_num_items()

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

    def get_source(self):
        raise NotImplementedError

    def get_sink(self):
        raise NotImplementedError

    def get_dataprovider(self, name):
        """
        Return a DP identified by a given name
        """
        wrapper = None
        for dp in self.model.get_all_modules():
            if dp.classname == name:
                wrapper = self.model.get_new_module_instance(dp.get_key())

        ok("Find wrapper '%s'" % name, wrapper != None)
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
                    [],
                    dp,
                    True
                    )

        return wrapper
