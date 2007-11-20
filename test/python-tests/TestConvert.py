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

#Dynamically load all datasources, datasinks and converters
type_converter = SimpleTest().type_converter

#Dictionary of information used to test the conversion functions
#
#The conversion function is called to construct a new type
#the data passed to the conversion funtion is the value of the conversion
#specific data corresponding to the type being converted into.
#
#the value corresponding to key * is used if there is no other key, otherwise
#None is passed. These should correspond to a filename of a file in the data dir
#
#    type           #construction function      #dict of conversion specific data
TYPES = {
    "file"      :   (new_file,      {"event":"1.ical", "contact":"1.vcard"} ),
    "note"      :   (new_note,      {}                                      ),
    "event"     :   (new_event,     {"*":"1.ical"}                          ),
    "contact"   :   (new_contact,   {"*":"1.vcard"}                         ),
    "email"     :   (new_email,     {}                                      )
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
            if type_converter._conversion_exists(i,j):
                conversions.append("Y")
                tests.append((i,j))
            else:
                conversions.append("N")
    print row(conversions)

print "Key"
print "%s: Conversion possible" % pad("Y")
print "%s: No conversion possible" % pad("N")

#now test all the conversions
for fromtype,totype in tests:
    conv = "%s --> %s" % (fromtype,totype)
    toinstance = None
    try:
        #unpack the conversion function and see what specific filename
        #contains data to make the conversion valid
        func, datadict = TYPES[fromtype]
        if datadict.has_key(totype):
            filename = datadict[totype]
        elif datadict.has_key("*"):
            filename = datadict["*"]
        else:
            filename = None
        #call the construction function with the appropriate data 
        #to make a new instance
        frominstance = func(filename)

        #convert
        toinstance = type_converter.convert(fromtype,totype,frominstance)
        ok("[%s] Conversion Successful" % conv,toinstance != None, False)
        #check that all info was retained
        retained = toinstance.get_UID() == frominstance.get_UID()
        ok("[%s] UID retained (%s vs. %s)" % (conv,frominstance.get_UID(),toinstance.get_UID()), retained, False)
        retained = toinstance.get_open_URI() == frominstance.get_open_URI()
        ok("[%s] Open URI retained (%s vs. %s)" % (conv,frominstance.get_open_URI(),toinstance.get_open_URI()), retained, False)
    except Exception:
        ok("[%s] Conversion Failed\n%s" % (conv,traceback.format_exc()), False, False)

finished()

