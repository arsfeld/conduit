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
                "baz,baz/bob"       : self.convert
        }
    #no-op
    def convert(self, data, **kwargs):
        return data

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
    #from       #to             #expected conversion sequence
    ("foo",     "foo",          ("foo->foo",)),
    ("foo",     "foo/bar",      ("foo->foo/bar",)),
    ("foo/bar", "foo",          ("foo->foo",)),
    ("foo",     "baz",          ("foo->baz",)),
    ("foo",     "baz/bob",      ("foo->baz","baz->baz/bob")),
    ("foo/bar", "baz/bob",      ("foo->baz","baz->baz/bob")),
    ("baz/bob", "baz/bob",      ("baz/bob->baz/bob",)),
    ("foo",     "bob",          False)
)

for f, t, expected in TEST_CONVERSIONS:
    if expected == False:
        ok("Conv %s -> %s doesnt exist" % (f,t), tc.conversion_exists(f,t) == False)
        try:
            tc.convert(f,t,FooData())
            ok("Invalid conversion exception caught", False)
        except Exceptions.ConversionDoesntExistError:
            ok("Invalid conversion exception caught", True)
    else:
        ok("Conv %s -> %s exists" % (f,t), tc.conversion_exists(f,t) == True)
        
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



