#common sets up the conduit environment
from common import *

import conduit.Utils as Utils
from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter

import os
import tempfile
import datetime
import traceback

WIDTH=9
def pad(s):
    return s+" "*(WIDTH-len(s))

def header(items):
    s = " "*WIDTH+"|"+"|".join([pad(i) for i in items])+"|"
    s += "\n"
    for i in items:
        s += "%s|" % ("-"*WIDTH)
    return s

def row(entries):
    s = ""
    for i in entries:
        s += "%s|" % pad(i)
    s += "\n"
    for i in entries:
        s += "%s|" % ("-"*WIDTH)
    return s

def tmpfile():
    fd, name = tempfile.mkstemp(prefix="conduit")
    os.close(fd)
    return name

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)
type_converter = TypeConverter(model)

    #type           #klass,                             #args
TYPES = {
    "file"      :   (conduit.datatypes.File.File,       {"URI":tmpfile()}),
    "note"      :   (conduit.datatypes.Note.Note,       {"title":Utils.random_string(),
                                                        "mtime":datetime.datetime(1967,3,23)}),
    "event"     :   (conduit.datatypes.Event.Event,     {"URI":Utils.random_string()}),
    "contact"   :   (conduit.datatypes.Contact.Contact, {"URI":Utils.random_string()}),
    "email"     :   (conduit.datatypes.Email.Email,     {"URI":Utils.random_string()})
    }

#Draw a table of the available conversions.
tests = []
print header(TYPES.keys())
for i in TYPES:
    conversions = [i]
    for j in TYPES:
        if i == j:
            conversions.append("N/A")
        else:
            if type_converter.conversion_exists(i,j,False):
                conversions.append("Y")
                tests.append((i,j))
            elif type_converter.conversion_exists(i,j,True):
                conversions.append("Y*")
            else:
                conversions.append("N")
    print row(conversions)

print "Key"
print "%s: Direct conversion possible" % pad("Y")
print "%s: Conversion goes via text (some info may be lost)" % pad("Y*")
print "%s: No conversion possible" % pad("N")

#now test all the conversions
for fromtype,totype in tests:
    fromklass,fromkwargs = TYPES[fromtype]
    frominstance = fromklass(**fromkwargs)

    toinstance = None
    try:
        toinstance = type_converter.convert(fromtype,totype,frominstance)
        ok("Converted %s --> %s" % (fromtype,totype), toinstance != None, False)
        #check that all info was retained
        retained = toinstance.get_mtime() == frominstance.get_mtime()
        ok("Mtime retained in conversion %s --> %s (%s vs. %s)" % (fromtype,totype,toinstance.get_mtime(),frominstance.get_mtime()), retained, False)
        retained = toinstance.get_UID() == frominstance.get_UID()
        ok("UID retained in conversion %s --> %s (%s vs. %s)" % (fromtype,totype,toinstance.get_UID(),frominstance.get_UID()), retained, False)
        retained = toinstance.get_open_URI() == frominstance.get_open_URI()
        ok("open URI retained in conversion %s --> %s (%s vs. %s)" % (fromtype,totype,toinstance.get_open_URI(),frominstance.get_open_URI()), retained, False)
    except Exception:
        ok("Converted %s --> %s\n%s" % (fromtype,totype,traceback.format_exc()), False, False)
