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

#Functions to construct new types
def new_file():
    fd, name = tempfile.mkstemp(prefix="conduit")
    os.close(fd)
    return conduit.datatypes.File.File(
                name
                )

def new_note():
    return conduit.datatypes.Note.Note(
                title=Utils.random_string(),
                mtime=datetime.datetime(1977,3,23)
                )

def new_event():
    icals = get_files_from_data_dir("1.ical")
    e = conduit.datatypes.Event.Event(
                URI=Utils.random_string()
                )
    f = open(icals[0],'r')
    e.set_from_ical_string(f.read())
    f.close()
    return e

def new_contact():
    vcards = get_files_from_data_dir("1.vcard")
    c = conduit.datatypes.Contact.Contact(
                URI=Utils.random_string()
                )
    f = open(vcards[0],'r')
    c.set_from_vcard_string(f.read())
    f.close()
    return c

def new_email():
    return conduit.datatypes.Email.Email(
                URI=Utils.random_string()
                )

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)
type_converter = TypeConverter(model)

    #type           #construction function
TYPES = {
    "file"      :   new_file,
    "note"      :   new_note,
    "event"     :   new_event,
    "contact"   :   new_contact,
    "email"     :   new_email
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
    conv = "%s --> %s" % (fromtype,totype)
    toinstance = None
    try:
        #call the construction function to make a new instance
        frominstance = TYPES[fromtype]()
        #convert
        toinstance = type_converter.convert(fromtype,totype,frominstance)
        ok("[%s] Conversion Successful" % conv,toinstance != None, False)
        #check that all info was retained
        retained = toinstance.get_mtime() == frominstance.get_mtime()
        ok("[%s] Mtime retained (%s vs. %s)" % (conv,toinstance.get_mtime(),frominstance.get_mtime()), retained, False)
        retained = toinstance.get_UID() == frominstance.get_UID()
        ok("[%s] UID retained (%s vs. %s)" % (conv,toinstance.get_UID(),frominstance.get_UID()), retained, False)
        retained = toinstance.get_open_URI() == frominstance.get_open_URI()
        ok("[%s] Open URI retained (%s vs. %s)" % (conv,toinstance.get_open_URI(),frominstance.get_open_URI()), retained, False)
    except Exception:
        ok("[%s] Conversion Failed\n%s" % (conv,traceback.format_exc()), False, False)
