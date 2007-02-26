#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter


#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)
type_converter = TypeConverter(model)

TYPES = {
    "file"      :   conduit.datatypes.File.File,
    "note"      :   conduit.datatypes.Note.Note,
    "event"     :   conduit.datatypes.Event.Event,
    "contact"   :   conduit.datatypes.Contact.Contact,
    "email"     :   conduit.datatypes.Email.Email
    }

WIDTH=9
def pad(s):
    return s+" "*(WIDTH-len(s))

def header(items):
    s = " "*WIDTH+"|"+"|".join([pad(i) for i in items])+"|"
    s += "\n"
    for i in items:
        s += "%s|" % ("-"*WIDTH)
    return s

def row(entries, header):
    s = ""
    for i in entries:
        s += "%s|" % pad(i)
    s += "\n"
    for i in entries:
        s += "%s|" % ("-"*WIDTH)
    return s

#Draw a table of the available conversions
print header(TYPES.keys())
for i in TYPES:
    conversions = [i]
    for j in TYPES:
        if i == j:
            conversions.append("N/A")
        else:
            if type_converter.conversion_exists(i,j,False):
                conversions.append("Y")
            elif type_converter.conversion_exists(i,j,True):
                conversions.append("Y*")
            else:
                conversions.append("N")
    print row(conversions,TYPES.keys())

print "Key"
print "%s: Direct conversion possible" % pad("Y")
print "%s: Conversion goes via text (some info may be lost)" % pad("Y*")
print "%s: No conversion possible" % pad("N")


