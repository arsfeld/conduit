import gobject
import random
import datetime
import thread
import time
import os.path
import logging
log = logging.getLogger("modules.Test")

import conduit
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.SimpleFactory as SimpleFactory
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
import conduit.Web as Web
from conduit.datatypes import Rid, DataType, Text, Video, Audio, File

MODULES = {
    "TestSource" :              { "type": "dataprovider" },
    "TestSink" :                { "type": "dataprovider" },
    "TestWebTwoWay" :           { "type": "dataprovider" },
    "TestFileSource" :          { "type": "dataprovider" },
    "TestFileSink" :            { "type": "dataprovider" },
    "TestImageSink" :           { "type": "dataprovider" },
    "TestVideoSink" :           { "type": "dataprovider" },
    "TestAudioSink" :           { "type": "dataprovider" },
    "TestConflict" :            { "type": "dataprovider" },
    "TestConversionArgs" :      { "type": "dataprovider" },
    "TestTwoWay" :              { "type": "dataprovider" },
    "TestSinkFailRefresh" :     { "type": "dataprovider" },
    "TestSinkNeedConfigure" :   { "type": "dataprovider" },
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

class _TestBase(DataProvider.DataProviderBase):
    def __init__(self):
        DataProvider.DataProviderBase.__init__(self)
        #Through an error on the nth time through
        self.errorAfter = 999
        self.newHash = False
        self.newMtime = False
        self.slow = False
        self.UID = Utils.random_string()
        self.numData = 5
        #Variables to test the config fuctions
        self.aString = ""
        self.aInt = 0
        self.aBool = False
        self.aList = []
        self.count = 0
        
    def initialize(self):
        return True

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setError(param):
            self.errorAfter = int(param)
        def setSlow(param):
            self.slow = bool(param)
        def setNewHash(param):
            self.newHash = bool(param)
        def setNewMtime(param):
            self.newMtime = bool(param)
        def setUID(param):
            self.UID = str(param)        
        def setNumData(param):
            self.numData = int(param)
        items = [
                    {
                    "Name" : "Error At:",
                    "Widget" : gtk.Entry,
                    "Callback" : setError,
                    "InitialValue" : self.errorAfter
                    },
                    {
                    "Name" : "Take a Long Time?",
                    "Widget" : gtk.CheckButton,
                    "Callback" : setSlow,
                    "InitialValue" : self.slow
                    },
                    {
                    "Name" : "Data gets a New Hash",
                    "Widget" : gtk.CheckButton,
                    "Callback" : setNewHash,
                    "InitialValue" : self.newHash
                    },
                    {
                    "Name" : "Data gets a New Mtime",
                    "Widget" : gtk.CheckButton,
                    "Callback" : setNewMtime,
                    "InitialValue" : self.newMtime
                    },
                    {
                    "Name" : "UID",
                    "Widget" : gtk.Entry,
                    "Callback" : setUID,
                    "InitialValue" : self.UID
                    },
                    {
                    "Name" : "Num Data",
                    "Widget" : gtk.Entry,
                    "Callback" : setNumData,
                    "InitialValue" : self.numData
                    } 
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def get_UID(self):
        return self.UID
        
    def get_configuration(self):
        return {
            "errorAfter" : self.errorAfter,
            "slow" : self.slow,
            "newHash" : self.newHash,
            "newMtime" : self.newMtime,
            "UID" : self.UID,
            "aString" : "im a string",
            "aInt" : 5,
            "aBool" : True,
            "aList" : ["ListItem1", "ListItem2"]
            }
            
class _TestConversionBase(DataProvider.DataSink):
    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.encodings =  {}
        self.encoding = "unchanged"

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        encodings = self.encodings.keys()+["unchanged"]
        items = [
                    {
                    "Name" : "Format (%s)" % ",".join(encodings),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def get_input_conversion_args(self):
        try:
            return self.encodings[self.encoding]
        except KeyError:
            #HACK: Any conversion arg is allowed for test data type...
            if self._in_type_ == "test_type":
                return {"arg":self.encoding}
            else:
                return {}
            
    def get_configuration(self):
        return {'encoding':self.encoding}

    def get_UID(self):
        return Utils.random_string()

class TestSource(_TestBase, DataProvider.DataSource):

    _name_ = "Test Source"
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "source"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "go-next"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSource.__init__(self)
        self.data = []
        self.numData = 10
        
        #signal we have new data in a few seconds
        gobject.timeout_add(3000, self._emit_change)

    def _emit_change(self):
        self.emit_change_detected()
        return False
        
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
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "edit-redo"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSink.__init__(self)
        
    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        if self.slow:
            time.sleep(1)    
        if self.count >= self.errorAfter:
            raise Exceptions.SyncronizeError("Error After:%s Count:%s" % (self.errorAfter, self.count))
        self.count += 1
        newData = TestDataType(data.get_UID())
        return newData.get_rid()
        
class TestTwoWay(TestSource, TestSink):

    _name_ = "Test Two Way"
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "view-refresh"

    def __init__(self, *args):
        TestSource.__init__(self)
        TestSink.__init__(self)

class TestFileSource(DataProvider.DataSource):

    _name_ = "Test File Source"
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"
    
    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        files = [
            os.path.join(conduit.SHARED_DATA_DIR,"conduit-splash.png"),
            __file__
            ]
        return files
        
    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        f = File.File(URI=LUID)
        f.set_open_URI(LUID)
        f.set_UID(LUID)
        return f
        
    def get_UID(self):
        return Utils.random_string()
        
class TestFileSink(DataProvider.DataSink):

    _name_ = "Test File Sink"
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)

    def put(self, data, overwrite, LUID=None):
        log.debug("Putting file: %s" % data._get_text_uri())
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_size())
        return newData.get_rid()

    def get_UID(self):
        return Utils.random_string()

class TestImageSink(Image.ImageSink):

    _name_ = "Test Image Sink"
    _icon_ = "image-x-generic"
    _category_ = conduit.dataproviders.CATEGORY_TEST

    def __init__(self, *args):
        Image.ImageSink.__init__(self)

        self.format = "image/jpeg"
        self.defaultFormat = "image/jpeg"
        self.size = "640x480"

    #ImageSink Methods
    def _upload_photo(self, uploadInfo):
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

    #DataProvider Methods
    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setFormat(param):
            self.format = str(param)
        def setDefaultFormat(param):
            self.defaultFormat = str(param)
        def setSize(param):
            self.size = str(param)

        items = [
                    {
                    "Name" : "Format",
                    "Widget" : gtk.Entry,
                    "Callback" : setFormat,
                    "InitialValue" : self.format
                    },
                    {
                    "Name" : "Default Format",
                    "Widget" : gtk.Entry,
                    "Callback" : setDefaultFormat,
                    "InitialValue" : self.defaultFormat
                    },
                    {
                    "Name" : "Size",
                    "Widget" : gtk.Entry,
                    "Callback" : setSize,
                    "InitialValue" : self.size
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()
        
    def is_configured (self):
        return True

    def get_UID(self):
        return Utils.random_string()

class TestConversionArgs(_TestConversionBase):

    _name_ = "Test Conversion Args"
    _description_ = "Pass args to converters"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "emblem-system"

    def __init__(self, *args):
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
        _TestConversionBase.__init__(self)
        TestFileSink.__init__(self)
        self.encoding = "ogg"
        self.encodings = Video.PRESET_ENCODINGS.copy()

class TestAudioSink(_TestConversionBase, TestFileSink):

    _name_ = "Test Audio Sink"
    _module_type_ = "sink"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "audio-x-generic"

    def __init__(self, *args):
        _TestConversionBase.__init__(self)
        TestFileSink.__init__(self)
        self.encoding = "ogg"
        self.encodings = Audio.PRESET_ENCODINGS.copy()

class TestWebTwoWay(TestTwoWay):

    _name_ = "Test Web"
    _description_ = "Launches Conduits Browser"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "applications-internet"

    def __init__(self, *args):
        TestTwoWay.__init__(self)
        self.url = "http://www.google.com"
        self.browser = "gtkmozembed"

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setUrl(param):
            self.url = str(param)
        def setBrowser(param):
            self.browser = str(param)

        items = [
                    {
                    "Name" : "Url",
                    "Widget" : gtk.Entry,
                    "Callback" : setUrl,
                    "InitialValue" : self.url
                    },
                    {
                    "Name" : "Browser",
                    "Widget" : gtk.Entry,
                    "Callback" : setBrowser,
                    "InitialValue" : self.browser
                    }

                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def _login(self):
        return True

    def refresh(self):
        TestTwoWay.refresh(self)
        log.debug("REFRESH (thread: %s)" % thread.get_ident())
        Web.LoginMagic(self._name_, self.url, browser=self.browser, login_function=self._login)

class TestSinkNeedConfigure(_TestBase, DataProvider.DataSink):

    _name_ = "Test Need Configure"
    _description_ = "Test Sink Needs Configuration"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "preferences-system"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSink.__init__(self)
        self.need_configuration(True)
        
    def configure(self, window):
        self.set_configured(True)

    def set_configuration(self, config):
        self.set_configured(True)

class TestSinkFailRefresh(_TestBase, DataProvider.DataSink):

    _name_ = "Test Fail Refresh"
    _description_ = "Test Sink Fails Refresh"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "dialog-error"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSink.__init__(self)
        
    def refresh(self):
        DataProvider.DataSink.refresh(self)
        raise Exceptions.RefreshError

class TestConflict(DataProvider.DataSink):

    _name_ = "Test Conflict"
    _description_ = "Test Sink Conflict"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "dialog-warning"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)

    def refresh(self):
        DataProvider.DataSink.refresh(self)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        if not overwrite:
            raise Exceptions.SynchronizeConflictError(conduit.datatypes.COMPARISON_UNKNOWN, data, TestDataType('0'))
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def get_UID(self):
        return Utils.random_string()

class TestConverter:
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
                             klass=type("DynamicTestSource3", (TestSource, ), {"_name_":"Dynamic Source 3"}),
                             initargs=("Baz","Foo"), 
                             category=conduit.dataproviders.CATEGORY_TEST)
        #run once
        return False


    def remove_one(self, *args):
        self.emit_removed(self.key1)
        return False

class TestFactoryRemoval(DataProvider.DataProviderFactory):
    """
    Repeatedly add/remove a DP/Category to stress test framework
    """
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)
        self.count = 200
        self.stats = Utils.Memstats()
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
        self.stats = Utils.Memstats()

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

