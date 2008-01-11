#common sets up the conduit environment
from common import *
import conduit.Utils as Utils
import conduit.datatypes.DataType as DataType
import conduit.Exceptions as Exceptions

class FooData(DataType.DataType):
    _name_ = "foo"
    def __init__(self):
        DataType.DataType.__init__(self)
        
class FooConverter(object):
    def __init__(self):
        self.conversions =  {
                "foo,foo"           : self.convert,     #transcode
                "foo,foo/bar"       : self.convert,
                "foo/bar,foo/bar"   : self.convert,     #transcode
                "foo,baz"           : self.convert,
                "baz,baz/bob"       : self.convert,
                "conversion,error"  : self.dont_convert,
        }
    def convert(self, data, **kwargs):
        return data
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
    #from           #to             #exist  #expected conversion sequence
    ("foo",         "foo",          True,   ("foo->foo",)),
    ("foo",         "foo/bar",      True,   ("foo->foo/bar",)),
    ("foo/bar",     "foo",          True,   ("foo->foo",)),
    ("foo",         "baz",          True,   ("foo->baz",)),
    ("foo",         "baz/bob",      True,   ("foo->baz","baz->baz/bob")),
    ("foo/bar",     "baz/bob",      True,   ("foo->baz","baz->baz/bob")),
    ("baz/bob",     "baz/bob",      True,   ("baz/bob->baz/bob",)),
    ("no",          "conversion",   False,  False),
    ("conversion",  "error",        True,   False)
)

for f, t, exist, expected in TEST_CONVERSIONS:
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
        
        data = FooData()
        newdata = tc.convert(f,t,data)
        ok("Data converted ok (no args)", data == newdata)

        #check conversion args are handled
        args = {"arg1":Utils.random_string(),"arg2":Utils.random_string()}
        conversions = tc._get_conversions(f,"%s?%s" % (t,Utils.encode_conversion_args(args)))
        ok("Conversion args passed to last converter", conversions[-1][-1] == args)            
        newdata = tc.convert(f,"%s?%s"%(t,Utils.encode_conversion_args(args)),data)
        ok("Data converted ok (with args)", data == newdata)

finished()



