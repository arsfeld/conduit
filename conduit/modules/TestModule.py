import gobject
import random
import datetime
import thread
import time
import os.path
import logging
log = logging.getLogger("modules.Test")

import conduit
import conduit.utils as Utils
import conduit.utils.Memstats as Memstats
import conduit.TypeConverter as TypeConverter
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.SimpleFactory as SimpleFactory
import conduit.dataproviders.Image as Image
import conduit.dataproviders.File as FileDataProvider
import conduit.modules.iPodModule.iPodModule as iPodModule
import conduit.Exceptions as Exceptions
import conduit.Web as Web
from conduit.datatypes import Rid, DataType, Text, Video, Audio, File

MODULES = {
    "TestEasyConfig" :          { "type": "dataprovider" },
    "TestSource" :              { "type": "dataprovider" },
    "TestSink" :                { "type": "dataprovider" },
    "TestWebTwoWay" :           { "type": "dataprovider" },
    "TestFileSource" :          { "type": "dataprovider" },
    "TestFileSink" :            { "type": "dataprovider" },
    "TestFileTwoWay" :          { "type": "dataprovider" },
    "TestFolderTwoWay" :        { "type": "dataprovider" },
    "TestImageSink" :           { "type": "dataprovider" },
    "TestVideoSink" :           { "type": "dataprovider" },
    "TestAudioSink" :           { "type": "dataprovider" },
    "TestConflict" :            { "type": "dataprovider" },
    "TestConversionArgs" :      { "type": "dataprovider" },
    "TestTwoWay" :              { "type": "dataprovider" },
    "TestFailRefresh" :         { "type": "dataprovider" },
    "TestSinkNeedConfigure" :   { "type": "dataprovider" },
    "TestiPodMusic" :           { "type": "dataprovider" },
    "TestiPodVideo" :           { "type": "dataprovider" },
    "TestFactory" :             { "type": "dataprovider-factory" },
#    "TestFactoryRemoval" :      { "type": "dataprovider-factory" },
#    "TestSimpleFactory" :       { "type": "dataprovider-factory" },
    "TestConverter" :           { "type": "converter" }
}

DEFAULT_MTIME=datetime.datetime(2003,8,16)
DEFAULT_HASH="12345"

#Test datatype is a thin wrapper around a string in the form
#"xy.." where x is an integer, and y is a string
class TestDataType(DataType.DataType):
    _name_ = "test_type"
    def __init__(self, Integer, mtime=DEFAULT_MTIME, hash=DEFAULT_HASH):
        DataType.DataType.__init__(self)
        self.Integer = int(Integer)
        self.myHash = hash

        #WARNING: Datatypes should not call these function from within
        #their constructor - that is the dataproviders responsability. Consider
        #this a special case for testing
        self.set_UID(str(Integer))        
        self.set_open_URI("file:///home/")
        self.set_mtime(mtime)
        
    def __str__(self):
        return "testData %s" % self.Integer

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['Integer'] = self.Integer
        data['myHash'] = self.myHash
        return data

    def __setstate__(self, data):
        self.Integer = data['Integer']
        self.myHash = data['myHash']
        DataType.DataType.__setstate__(self, data)

    def get_hash(self):
        return self.myHash

    def get_snippet(self):
        return str(self) + "\nI am a piece of test data"
     
    #The strings are numerically compared. If A < B then it is older
    #If A is larger than B then it is newer.
    def compare(self, B):
        a = self.Integer
        b = B.Integer
        if a < b:
            return conduit.datatypes.COMPARISON_OLDER
        elif a > b:
            return conduit.datatypes.COMPARISON_NEWER
        elif a == b:
            return conduit.datatypes.COMPARISON_EQUAL
        else:
            return conduit.datatypes.COMPARISON_UNKNOWN

class TestEasyConfig(DataProvider.DataProviderBase):
    _name_ = "Test EasyConfig"
    _description_ = "Testes the EasyConfigurator"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "source"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "preferences-desktop"
    _configurable_ = True
    
    def __init__(self):
        DataProvider.DataProviderBase.__init__(self)
        self.update_configuration(
            folder = ('', self._set_folder, lambda: self.folder),
            checktest = "Choice 3",
            number = 0,
            items = [],
            password = '',
        )

    def _set_folder(self, f):
        self.folder = f
        
    def config_setup(self, config):
        status_label = config.add_item("Status label", "label")
        def status_changed(config, item):
            status_label.value = "%s: %s" % (item.title, item.value)
        config.connect("item-changed", status_changed)
        
        def change_label_callback(button_item):
            status_label.value = text_config.value
        text_config = config.add_item("Type some text", "text", initial_value = "Then click below")    
        config.add_item("Change label", "button", initial_value = change_label_callback)
        
        config.add_section("Section")
        config.add_item("Select folder", "filebutton", order = 1,
            config_name = "folder",
            directory = True,
        )
        #The next item shows most choice-based features.
        radio_config = config.add_item("Radio button test", "radio",
            config_name = "checktest",
            choices = [1, ("My value 2", "Choice 2"), "Choice 3"],
        )
        
        #Defining a order prioritize sections. The grouping is done by sections
        #of the same order, then on the order they were declared.
        #So, even if this is declared here, because it has order 1, it will be
        #below all other sections, which are order -1 by default.
        #This allows for subclasses to put sections below or above it's parents
        #sections.
        config.add_section('Section', order = 1)
        combo_config = config.add_item("Combo test", "combo",
            initial_value = 0,
            choices = [choice for choice in enumerate(["Choice %s" % i for i in range(5)])],
        )
        
        config.add_item("Number", "spin",
            config_name = "number",
            maximum = 100,
        )

        #These items will actually be added in "Section 1" defined above, 
        #because by default it will look for existing sections with this title
        section = config.add_section("Section")
        items_config = config.add_item("Items", "list",
            config_name = "items",
            # The actual value returned from this list would be either True or
            # False, but their text would be tst and tst2 respectively
            choices = [("Value 1", "Item with value 1"), ("Value 2","Item with value 2"), "Value 3"],
        )
        config.add_item("Password", "text",
            config_name = "password",
            password = True
        )
        
        #use_existing allows for duplicate sections with the same title.
        #By default, and prefereable, adding another with the same title, adds
        #items to the existing section instead of creating a new one.
        #Please keep in mind two sections with the same title is very confusing.
        #config.add_section("Section 1", use_existing = False)
        def button_clicked(button):
            #A list is smart enough to detect if choices contain tuples with
            #values and labels, or just labels.
            items_config.choices = ['Test1', 'Test2', 'Test3', 'Test4', 'Test5']
            #items_config.enabled = not items_config.enabled
            section.enabled = not section.enabled
            
        #Adding an empty section actually puts next items unidented in the
        #configuration dialog, so it looks to be outside a section.
        config.add_section()            
        config.add_item("Disable section / Change choices", "button",
            initial_value = button_clicked
        )

class _TestBase:
    _configurable_ = True
    def __init__(self):
        self.update_configuration(
            errorAfter = 999,
            errorFatal = False,
            newHash = False,
            newMtime = False,
            slow = False,
            UID = Utils.random_string(),
            numData = 5,
            #Variables to test the config fuctions
            aString = "",
            aInt = 0,
            aBool = False,
            aList = [],
            count = 0,
        )
        
    def _change_detected(self, *args):
        gobject.timeout_add(3000, self.emit_change_detected)    
        
    def initialize(self):
        return True

    def config_setup(self, config):
        config.add_section("Basic Settings")
        config.add_item("Error at", "spin", config_name = "errorAfter")
        config.add_item("Fatal Error?", "check", config_name = "errorFatal")
        config.add_item("Data gets a new hash", 'check', config_name = 'newHash')
        config.add_item('Data gets a new mtime', 'check', config_name = 'newMtime')
        config.add_item("Take a long time", 'check', config_name = "slow")
        config.add_item('UID', 'text', config_name = 'UID')
        config.add_item('Num data', 'spin', config_name = 'numData')
        config.add_item('Emit change detected', 'button', initial_value = lambda b: self._change_detected())
        
    def get_UID(self):
        return self.UID
   
class _TestConversionBase:
    _configurable_ = True

    def __init__(self):
        self.encodings = {}
        self.update_configuration(
            encoding = "ogg",
        )

    def config_setup(self, config):
        config.add_section("Conversion Settings")
        config.add_item("Format:", "combo",
            choices = [(name, opts['description'] or name) for name, opts in self.encodings.iteritems()],
            config_name = 'encoding'
        )
        #FIXME Add None as conversion option

    def get_input_conversion_args(self):
        try:
            return self.encodings[self.encoding]
        except KeyError:
            #HACK: Any conversion arg is allowed for test data type...
            if self._in_type_ == "test_type":
                return {"arg":self.encoding}
            else:
                return {}
            
    def get_UID(self):
        return Utils.random_string()

class TestSource(_TestBase, DataProvider.DataSource):

    _name_ = "Test Source"
    _description_ = "Emits TestDataTypes"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "source"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "go-next"
    
    DEFAULT_NUM_DATA = 10

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self, *args)
        _TestBase.__init__(self)
        self.data = []
        self.numData = self.DEFAULT_NUM_DATA
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.data = []
        #Assemble a random array of data
        for i in range(0, random.randint(1, self.numData)):
            self.data.append(str(i))
       
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        data = []
        for i in range(0,self.numData):
            data.append(str(i))
        return data

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        if self.slow:
            time.sleep(1)

        index = int(LUID)
        if index >= self.errorAfter:
            if self.errorFatal:
                raise Exceptions.SyncronizeFatalError("Error After:%s Count:%s" % (self.errorAfter, index))
            else:
                raise Exceptions.SyncronizeError("Error After:%s Count:%s" % (self.errorAfter, index))

        mtime = DEFAULT_MTIME
        if self.newMtime:
            mtime = datetime.datetime.now()
            
        hash = DEFAULT_HASH
        if self.newHash:
            hash = Utils.random_string()

        data = TestDataType(LUID, mtime, hash)
        return data

    def add(self, LUID):
        return True
        
    def finish(self, aborted, error, conflict): 
        DataProvider.DataSource.finish(self)
        self.data = []
		
class TestSink(_TestBase, DataProvider.DataSink):

    _name_ = "Test Sink"
    _description_ = "Consumes TestDataTypes"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "edit-redo"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self, *args)
        _TestBase.__init__(self)
        
    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        if self.slow:
            time.sleep(1)    
        if self.count >= self.errorAfter:
            if self.errorFatal:
                raise Exceptions.SyncronizeFatalError("Error After:%s Count:%s" % (self.errorAfter, self.count))
            else:
                raise Exceptions.SyncronizeError("Error After:%s Count:%s" % (self.errorAfter, self.count))
        self.count += 1
        newData = TestDataType(data.get_UID())
        return newData.get_rid()
        
class TestTwoWay(TestSource, TestSink):

    _name_ = "Test Two Way"
    _description_ = "Sync TestDataTypes"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "view-refresh"

    def __init__(self, *args):
        TestSource.__init__(self)
        TestSink.__init__(self)

class TestFileSource(_TestBase, DataProvider.DataSource):

    _name_ = "Test File Source"
    _description_ = "Emits Files"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"
    
    def __init__(self, *args):
        DataProvider.DataSource.__init__(self, *args)
        _TestBase.__init__(self)
        self.UID = Utils.random_string()
        
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        files = [
            "file://"+os.path.join(conduit.SHARED_DATA_DIR,"conduit-splash.png"),
            "file://"+__file__
            ]
        return files
        
    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        f = File.File(URI=LUID)
        f.set_open_URI(LUID)
        f.set_UID(LUID)
        return f
        
class TestFileSink(_TestBase, DataProvider.DataSink):

    _name_ = "Test File Sink"
    _description_ = "Consumes Files"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self, *args)
        _TestBase.__init__(self)
        self.folder = "file://"+Utils.new_tempdir()

    def put(self, data, overwrite, LUID=None):
        log.debug("Putting file: %s" % data._get_text_uri())
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        if LUID == None:
            LUID = self.folder+os.sep+data.get_filename()
        data.transfer(LUID,overwrite)
        data.set_UID(LUID)
        return data.get_rid()
        
class TestFileTwoWay(TestFileSource, TestFileSink):

    _name_ = "Test File Two Way"
    _description_ = "Sync Files"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        TestFileSource.__init__(self)
        TestFileSink.__init__(self)

class TestFolderTwoWay(FileDataProvider.FolderTwoWay):

    _name_ = "Test Folder Two Way"
    _description_ = "Sync Folders"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        #Put a single tempfile into a tempdir
        FileDataProvider.FolderTwoWay.__init__(
                            self,
                            folder= "file://"+Utils.new_tempdir(),
                            folderGroupName="Test",
                            includeHidden=False,
                            compareIgnoreMtime=False,
                            followSymlinks=False
                            )

    def get_UID(self):
        return self.folder

    def add(self, LUID):
        #Add a temp file to folder
        tmpfile = Utils.new_tempfile(Utils.random_string())
        self.put(tmpfile,True,None)

class TestImageSink(_TestBase, Image.ImageSink):

    _name_ = "Test Image Sink"
    _description_ = "Consumes Images"
    _icon_ = "image-x-generic"
    _category_ = conduit.dataproviders.CATEGORY_TEST

    def __init__(self, *args):
        Image.ImageSink.__init__(self, *args)
        _TestBase.__init__(self)
        self.update_configuration(
            format = "image/jpeg",
            defaultFormat = "image/jpeg",
            size = "640x480"
        )

    #ImageSink Methods
    def _upload_photo(self, uploadInfo):
        if self.slow:
            time.sleep(2)
        LUID = "%s%s%s" % (uploadInfo.name,uploadInfo.url,self._name_)
        return Rid(uid=LUID)

    def _get_photo_info(self, luid):
        return None

    def _get_photo_formats (self):
        return (self.format, )
        
    def _get_default_format (self):
        return self.defaultFormat
        
    def _get_photo_size (self):
        return self.size

    def config_setup(self, config):
        _TestBase.config_setup(self, config)
        config.add_section("Image Settings")
        config.add_item('Format', 'text', config_name = 'format')
        config.add_item('Default Format', 'text', config_name = 'defaultFormat')
        config.add_item('Size', 'text', config_name = 'size')
        
class TestConversionArgs(_TestConversionBase, TestSink):

    _name_ = "Test Conversion Args"
    _description_ = "Pass Arguments to TestConverter"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        TestSink.__init__(self)
        _TestConversionBase.__init__(self)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID())
        return newData.get_rid()

class TestVideoSink(_TestConversionBase, TestFileSink):

    _name_ = "Test Video Sink"
    _module_type_ = "sink"
    _in_type_ = "file/video"
    _out_type_ = "file/video"
    _icon_ = "video-x-generic"

    def __init__(self, *args):
        TestFileSink.__init__(self)
        _TestConversionBase.__init__(self)
        self.encodings = Video.PRESET_ENCODINGS.copy()

class TestAudioSink(_TestConversionBase, TestFileSink):

    _name_ = "Test Audio Sink"
    _module_type_ = "sink"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "audio-x-generic"

    def __init__(self, *args):
        TestFileSink.__init__(self)
        _TestConversionBase.__init__(self)
        self.encodings = Audio.PRESET_ENCODINGS.copy()

class TestWebTwoWay(TestTwoWay):

    _name_ = "Test Web"
    _description_ = "Launches Web Browser"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "applications-internet"
    _configurable_ = True

    def __init__(self, *args):
        TestTwoWay.__init__(self)
        self.update_configuration(
            url = "http://www.google.com",
            browser = conduit.BROWSER_IMPL
        )

    def config_setup(self, config):

        def _login(*args):
            log.debug("Logging in")
            Web.LoginMagic("The Internets", self.url, login_function=lambda: True)

        def _login_finished(*args):
            log.debug("Login finished")
            #Utils.dialog_reset_cursor(dlg)
            pass

        def _login_clicked(button):
            #Utils.dialog_set_busy_cursor(dlg)
            log.debug("Login clicked")
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                                            self,
                                            _login_finished,
                                            _login)

        TestTwoWay.config_setup(self, config)
        config.add_section("Browser Settings")
        config.add_item("Url", "text",
            config_name = 'url'
        )
        config.add_item("Browser", "text",
            config_name = "browser"
        )
        config.add_item("Launch Browser", "button", 
            initial_value = _login_clicked
        )

    def refresh(self):
        TestTwoWay.refresh(self)
        log.debug("REFRESH (thread: %s)" % thread.get_ident())
        Web.LoginMagic(self._name_, self.url, browser=self.browser, login_function=lambda: True)

class TestSinkNeedConfigure(_TestBase, DataProvider.DataSink):

    _name_ = "Test Need Configure"
    _description_ = "Needs Configuration"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "preferences-system"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self, *args)
        _TestBase.__init__(self)
        self.isConfigured = False
        
    def configure(self, window):
        self.isConfigured = True

    def set_configuration(self, config):
        self.isConfigured = True

    def is_configured(self, isSource, isTwoWay):
        return self.isConfigured

class TestFailRefresh(TestTwoWay):

    _name_ = "Test Fail Refresh"
    _description_ = "Fails Refresh"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "dialog-error"

    def __init__(self, *args):
        TestTwoWay.__init__(self)
        
    def refresh(self):
        TestTwoWay.refresh(self)
        raise Exceptions.RefreshError

class TestConflict(_TestBase, DataProvider.DataSink):

    _name_ = "Test Conflict"
    _description_ = "Raises a Conflict"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "dialog-warning"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self, *args)
        _TestBase.__init__(self)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID())
        if not overwrite:
            raise Exceptions.SynchronizeConflictError(conduit.datatypes.COMPARISON_UNKNOWN, data, newData)
        return newData.get_rid()

class TestiPodMusic(iPodModule.IPodMusicTwoWay):
    pass

class TestiPodVideo(iPodModule.IPodVideoTwoWay):
    pass

class TestConverter(TypeConverter.Converter):
    def __init__(self):
        self.conversions =  {
                "test_type,test_type"   : self.transcode,
                "text,test_type"        : self.convert_to_test,
                "test_type,text"        : self.convert_to_text,}
                            
    def transcode(self, test, **kwargs):
        log.debug("TEST CONVERTER: Transcode %s (args: %s)" % (test, kwargs))
        return test

    def convert_to_test(self, text, **kwargs):
        #only keep the first char
        char = text.get_string()[0]
        t = TestDataType(char)
        return t

    def convert_to_text(self, test, **kwargs):
        t = Text.Text(
                    text=test.integerData
                    )
        return t

class TestFactory(DataProvider.DataProviderFactory):
    _configurable_ = True
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)
        
        #callback the GUI in 5 seconds to add a new dataprovider
        gobject.timeout_add(4000, self.make_one)
        gobject.timeout_add(5000, self.make_two)
        gobject.timeout_add(6000, self.make_three)
        gobject.timeout_add(7000, self.remove_one)

        
    def make_one(self, *args):
        self.key1 = self.emit_added(
                            klass=type("DynamicTestSource1", (TestSource, ), {"_name_":"Dynamic Source 1"}),
                            initargs=("Foo",), 
                            category=conduit.dataproviders.CATEGORY_TEST)
        #run once
        return False

    def make_two(self, *args):
        self.key2 = self.emit_added(
                             klass=type("DynamicTestSource2", (TestSource, ), {"_name_":"Dynamic Source 2"}),
                             initargs=("Bar","Baz"), 
                             category=conduit.dataproviders.CATEGORY_TEST)
        #run once
        return False

    def make_three(self, *args):
        self.key3 = self.emit_added(
                             klass=type("TestSource", (TestSource, ), {"_name_":"Preconfigured Test Source", "DEFAULT_NUM_DATA":20}),
                             initargs=(), 
                             category=conduit.dataproviders.CATEGORY_TEST,
                             customKey="CustomKey")
        #run once
        return False


    def remove_one(self, *args):
        self.emit_removed(self.key1)
        return False

    def setup_configuration_widget(self):
        import gtk
        vb = gtk.VBox(2)
        vb.pack_start(gtk.Label("Hello World"))
        self.entry = gtk.Entry()
        vb.pack_start(self.entry)
        return vb

    def save_configuration(self, ok):
        log.debug("OK: %s Message: %s" % (ok,self.entry.get_text()))

class TestFactoryRemoval(DataProvider.DataProviderFactory):
    """
    Repeatedly add/remove a DP/Category to stress test framework
    """
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)
        self.count = 200
        self.stats = Memstats.Memstats()
        self.cat = DataProviderCategory.DataProviderCategory(
                    "TestHotplug",
                    "emblem-system",
                    "/test/")
        gobject.timeout_add(5000, self.added)

    def added(self):
        self.stats.calculate()
        self.key = self.emit_added(
                           klass=type("DynamicTestSource", (TestSource, ), {"_name_":"Dynamic Source"}),
                           initargs=("Bar","Bazzer"),
                           category=self.cat)
        gobject.timeout_add(500, self.removed)
        return False

    def removed(self):
        self.emit_removed(self.key)
        if self.count > 0:
            gobject.timeout_add(500, self.added)
            self.count -= 1
        else:
            self.stats.calculate()
        return False

    def quit(self):
        self.count = 0


class TestSimpleFactory(SimpleFactory.SimpleFactory):
    """
    Repeatedly add/remove a DP/Category to stress test framework
    """
    def __init__(self, **kwargs):
        SimpleFactory.SimpleFactory.__init__(self, **kwargs)
        gobject.timeout_add(5000, self._added)
        self.count = 200
        self.stats = Memstats.Memstats()

    def get_category(self, key, **kwargs):
        return DataProviderCategory.DataProviderCategory(
            "TestHotplug",
            "emblem-system",
            "/test/")

    def get_dataproviders(self, key, **kwargs):
        return [type("DynamicTestSource", (TestSource, ), {"_name_":"Dynamic Source"})]

    def get_args(self, key, **kwargs):
        return ()

    def _added(self):
        """ Some hal event added a device? """
        self.stats.calculate()
        self.item_added("foobar", **{})
        gobject.timeout_add(500, self._removed)
        return False

    def _removed(self):
        self.item_removed("foobar")
        if self.count > 0:
            gobject.timeout_add(500, self._added)
            self.count -= 1
        else:
            self.stats.calculate()
        return False

    def quit(self):
        self.count = 0

