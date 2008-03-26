#common sets up the conduit environment
from common import *
import conduit.utils as Utils
import conduit.datatypes.DataType as DataType
import conduit.Exceptions as Exceptions

class FooData(DataType.DataType):
    _name_ = "foo"
    def __init__(self):
        DataType.DataType.__init__(self)
        
class FooBarData(FooData):
    _name_ = "foo/bar"
    def __init__(self):
        FooData.__init__(self)
        
class BazData(DataType.DataType):
    _name_ = "baz"
    def __init__(self):
        DataType.DataType.__init__(self)
        
class BazBobData(BazData):
    _name_ = "baz/bob"
    def __init__(self):
        BazData.__init__(self)
        
class FooConverter(object):
    def __init__(self):
        self.conversions =  {
                "foo,foo"           : self.transcode,
                "foo,foo/bar"       : self.foo_to_foobar,
                "foo/bar,foo/bar"   : self.transcode,
                "foo,baz"           : self.foo_to_baz,
                "baz,baz/bob"       : self.baz_to_bazbob,
                "foo,error"         : self.dont_convert,
        }
    def transcode(self, data, **kwargs):
        return data
    def foo_to_foobar(self, data, **kwargs):
        return FooBarData()
    def foo_to_baz(self, data, **kwargs):
        return BazData()
    def baz_to_bazbob(self, data, **kwargs):
        return BazBobData()
    def dont_convert(self, data, **kwargs):
        raise Exception

test = SimpleTest()
tc = test.type_converter

#Add fooconverter
converterWrapper = test.wrap_dataprovider(FooConverter())
tc._add_converter(converterWrapper)

#check it picked up all the conversions
availableConversions =  tc.get_convertables_list()
for i in converterWrapper.module.conversions:
    f,t = i.split(',')
    ok("Conversion %s -> %s available" % (f,t),(f,t) in availableConversions)

#Conversions to try
TEST_CONVERSIONS = (
    #from           #from class     #to             #to class   #exist  #expected conversion sequence
    ("foo",         FooData,        "foo",          FooData,    True,   ("foo->foo",)),
    ("foo",         FooData,        "foo/bar",      FooBarData, True,   ("foo->foo/bar",)),
    ("foo/bar",     FooBarData,     "foo",          FooBarData, True,   ("foo->foo",)),
    ("foo",         FooData,        "baz",          BazData,    True,   ("foo->baz",)),
    ("foo",         FooData,        "baz/bob",      BazBobData, True,   ("foo->baz","baz->baz/bob")),
    ("foo/bar",     FooBarData,     "baz/bob",      BazBobData, True,   ("foo->baz","baz->baz/bob")),
    ("baz/bob",     BazBobData,     "baz/bob",      BazBobData, True,   ("baz/bob->baz/bob",)),
    ("foo",         FooData,        "error",        None,       True,   False),
    ("no",          None,           "conversion",   None,       False,  False),
)

for f, fKlass, t, tKlass, exist, expected in TEST_CONVERSIONS:
    ok("Conv %s -> %s exists (%s)" % (f,t,exist), tc.conversion_exists(f,t) == exist)
    if expected == False:
        try:
            tc.convert(f,t,FooData())
            ok("Conversion exception caught", False)
        except Exceptions.ConversionError:
            ok("ConversionError exception caught", True)
        except Exceptions.ConversionDoesntExistError:
            ok("ConversionDoesntExistError exception caught", True)
        except Exception:
            ok("Conversion exception caught", False)
    else:
        #check the correct conversions are predicted
        conversions = tc._get_conversions(f,t)
        ok("Correct num conversions predicted", len(expected) == len(conversions))
        i = 0
        for cf, ct, a in conversions:
            ef,et = expected[i].split("->")
            ok("Correct conversion: %s -> %s (v. %s -> %s)" % (cf,ct,ef,et), cf == ef and ct == et)
            i += 1
        
        data = fKlass()
        newdata = tc.convert(f,t,data)
        ok("Data converted ok (no args)", True)

        #check conversion args are handled
        args = {"arg1":Utils.random_string(),"arg2":Utils.random_string()}
        conversions = tc._get_conversions(f,"%s?%s" % (t,Utils.encode_conversion_args(args)))
        ok("Conversion args passed to last converter", conversions[-1][-1] == args)            
        newdata = tc.convert(f,"%s?%s"%(t,Utils.encode_conversion_args(args)),data)
        ok("Data converted ok (with args)", data._name_ == fKlass._name_ and newdata._name_ == tKlass._name_)

finished()



