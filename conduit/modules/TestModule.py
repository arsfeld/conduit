import gobject
import random
import datetime
import thread

import conduit
from conduit import logd
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.Image as Image
import conduit.Exceptions as Exceptions
import conduit.Module as Module
import conduit.Web as Web
#from conduit.datatypes import Rid
from conduit.datatypes import DataType, Text, Video, Audio

import time

MODULES = {
    "TestSource" :              { "type": "dataprovider" },
    "TestSink" :                { "type": "dataprovider" },
    "TestWebSink" :             { "type": "dataprovider" },
    "TestFileSink" :             { "type": "dataprovider" },
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
    "TestConverter" :           { "type": "converter" }
}

DEFAULT_MTIME=datetime.datetime(2003,8,16)
DEFAULT_HASH="12345"

#Test datatype is a thin wrapper around a string in the form
#"xy.." where x is an integer, and y is a string
class TestDataType(DataType.DataType):
    _name_ = "test_type"
    def __init__(self, xy, mtime=DEFAULT_MTIME, hash=DEFAULT_HASH):
        DataType.DataType.__init__(self)
        self.Integer = int(xy[0])
        self.myHash = hash
        
        self.set_open_URI("file:///home/")
        self.set_UID(xy)
        self.set_mtime(mtime)
        
    def __str__(self):
        return "testData %s" % self.charInteger

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
    def compare(self, A, B):
        a = A.Integer
        b = B.Integer
        if a < b:
            return conduit.datatypes.COMPARISON_OLDER
        elif a > b:
            return conduit.datatypes.COMPARISON_NEWER
        elif a == b:
            return conduit.datatypes.COMPARISON_EQUAL
        else:
            return conduit.datatypes.COMPARISON_UNKNOWN

class _TestBase:
    def __init__(self):
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
        
        #signal we have new data in a few seconds
        gobject.timeout_add(3000, self._emit_change)

    def _emit_change(self):
        self.emit_change_detected()
        return False
       
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        data = []
        for i in range(0,self.numData):
            data.append(str(i))
        return data

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        if self.slow:
            time.sleep(2)

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
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

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
        return uploadInfo.name+uploadInfo.url+self._name_

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

class TestVideoSink(DataProvider.DataSink):

    _name_ = "Test Video Sink"
    _module_type_ = "sink"
    _in_type_ = "file/video"
    _out_type_ = "file/video"
    _icon_ = "video-x-generic"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.encoding = "ogg"

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        items = [
                    {
                    "Name" : "Format (%s,unchanged)" % ",".join(Video.PRESET_ENCODINGS.keys()),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def get_input_conversion_args(self):
        try:
            return Video.PRESET_ENCODINGS[self.encoding]
        except KeyError:
            return {}

    def put(self, data, overwrite, LUID=None):
        logd("Put Video File: %s (stored at: %s)" % (data.get_UID(),data.get_local_uri()))
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def get_UID(self):
        return Utils.random_string()

class TestAudioSink(DataProvider.DataSink):

    _name_ = "Test Audio Sink"
    _module_type_ = "sink"
    _in_type_ = "file/audio"
    _out_type_ = "file/audio"
    _icon_ = "audio-x-generic"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.encoding = "ogg"

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setEnc(param):
            self.encoding = str(param)

        items = [
                    {
                    "Name" : "Format (%s,unchanged)" % ",".join(Audio.PRESET_ENCODINGS.keys()),
                    "Widget" : gtk.Entry,
                    "Callback" : setEnc,
                    "InitialValue" : self.encoding
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def get_input_conversion_args(self):
        try:
            return Audio.PRESET_ENCODINGS[self.encoding]
        except KeyError:
            return {}

    def put(self, data, overwrite, LUID=None):
        logd("Put Audio File: %s (stored at: %s)" % (data.get_UID(),data.get_local_uri()))
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def get_UID(self):
        return Utils.random_string()

class TestWebSink(DataProvider.DataSink):

    _name_ = "Test Web Sink"
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "applications-internet"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
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
        print "REFRESH ----------------------------", thread.get_ident()
        DataProvider.DataSink.refresh(self)
        Web.LoginMagic(self._name_, self.url, browser=self.browser, login_function=self._login)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

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
        logd("Putting file: %s" % data._get_text_uri())
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def get_UID(self):
        return Utils.random_string()


class TestTwoWay(_TestBase, DataProvider.TwoWay):

    _name_ = "Test Two Way"
    _description_ = "Prints Debug Messages"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "twoway"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "view-refresh"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.TwoWay.__init__(self)
        self.data = None
        self.numData = 10

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.data = []
        #Assemble a random array of data
        for i in range(0, random.randint(1, self.numData)):
            self.data.append(str(i))

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.data

    def get(self, LUID):
        if self.slow:
            time.sleep(1)    
        DataProvider.TwoWay.get(self, LUID)
        return TestDataType(LUID)

    def put(self, data, overwrite, LUID=None):
        if self.slow:
            time.sleep(1)    
        DataProvider.TwoWay.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def finish(self): 
        DataProvider.TwoWay.finish(self)
        self.data = None

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
            raise Exceptions.SynchronizeConflictError(conduit.datatypes.COMPARISON_UNKNOWN, data, TestDataType('0Conflict'))
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def get_UID(self):
        return Utils.random_string()

class TestConversionArgs(DataProvider.DataSink):

    _name_ = "Test Conversion Args"
    _description_ = "Pass args to converters"
    _category_ = conduit.dataproviders.CATEGORY_TEST
    _module_type_ = "sink"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.conversionArgs = ""

    def configure(self, window):
        import gtk
        import conduit.gtkui.SimpleConfigurator as SimpleConfigurator

        def setArgs(param):
            self.conversionArgs = str(param)
        items = [
                    {
                    "Name" : "Conversion Args (string)",
                    "Widget" : gtk.Entry,
                    "Callback" : setArgs,
                    "InitialValue" : self.conversionArgs
                    }
                ]
        dialog = SimpleConfigurator.SimpleConfigurator(window, self._name_, items)
        dialog.run()

    def refresh(self):
        DataProvider.DataSink.refresh(self)

    def put(self, data, overwrite, LUID=None):
        DataProvider.DataSink.put(self, data, overwrite, LUID)
        newData = TestDataType(data.get_UID()+self._name_)
        return newData.get_rid()

    def get_input_conversion_args(self):
        if self.conversionArgs == "":
            args = {}
        else:
            args = {
                "foo"   :   self.conversionArgs,
                "bar"   :   "baz"
                }
        return args

    def get_UID(self):
        return Utils.random_string()

class TestConverter:
    def __init__(self):
        self.conversions =  {
                "test_type,test_type"   : self.transcode,
                "text,test_type"        : self.convert_to_test,
                "test_type,text"        : self.convert_to_text,}
                            
    def transcode(self, test, **kwargs):
        logd("TEST CONVERTER: Transcode %s (args: %s)" % (test, kwargs))
        return test

    def convert_to_test(self, text, **kwargs):
        #only keep the first char
        char = text.get_string()[0]
        t = TestDataType(char)
        return t

    def convert_to_text(self, test, **kwargs):
        t = Text.Text(text=test.integerData)
        return t

class TestDynamicSource(_TestBase, DataProvider.DataSource):
    _name_ = "Test Dynamic Source"
    _description_ = "Prints Debug Messages"
    _module_type_ = "source"
    _in_type_ = "test_type"
    _out_type_ = "test_type"
    _icon_ = "emblem-system"

    def __init__(self, *args):
        _TestBase.__init__(self)
        DataProvider.DataSource.__init__(self)

class TestFactory(DataProvider.DataProviderFactory):
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)

        #callback the GUI in 5 seconds to add a new dataprovider
        gobject.timeout_add(3000, self.make_one)
        gobject.timeout_add(5000, self.make_two)
        gobject.timeout_add(7000, self.make_three)
        gobject.timeout_add(7000, self.remove_one)

        
    def make_one(self, *args):
        self.key1 = self.emit_added(
                            klass=TestDynamicSource,
                            initargs=("Foo",), 
                            category=conduit.dataproviders.CATEGORY_TEST)
        #run once
        return False

    def make_two(self, *args):
        self.key2 = self.emit_added(
                             klass=TestDynamicSource,
                             initargs=("Bar","Baz"), 
                             category=conduit.dataproviders.CATEGORY_TEST)
        #run once
        return False

    def make_three(self, *args):
        self.key3 = self.emit_added(
                             klass=TestTwoWay,
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
        gobject.timeout_add(5000, self.added)
        self.count = 200
        self.stats = None

        self.cat = DataProvider.DataProviderCategory(
                    "TestHotplug",
                    "emblem-system",
                    "/test/")

    def added(self):
        if self.stats == None:
            self.stats = Utils.memstats()

        self.key = self.emit_added(
                           klass=TestDynamicSource,
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
            Utils.memstats(self.stats)
        return False

    def quit(self):
        self.count = 0


