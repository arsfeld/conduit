#common sets up the conduit environment
from common import *

import pickle

#It seems to need this in order for other import 
#functions to work...
test = SimpleTest()

TYPES = {
    #name               #construction function
    "file"          :   new_file,
    "note"          :   new_note,
    "event"         :   new_event,
    "contact"       :   new_contact,
    "email"         :   new_email,
    "text"          :   new_text,
    "setting"       :   new_setting,
    "test"          :   new_test_datatype,
    "photo"         :   new_photo,
    }

for t,func in TYPES.items():
    orig = func(None)
    ok("%s: Created new instance" % t, orig != None)
    ok("%s: get_UID() implemented" % t, orig.get_UID() != None)
    ok("%s: get_rid() works" % t, orig.get_rid() != None)
    
    #pickle to a string
    dump = pickle.dumps(orig)
    ok("%s: Instace pickles to str" % t, type(dump) == str and len(dump) > 0)
    
    #get back again
    clone = pickle.loads(dump)
    ok("%s: Instace un-pickles to same type" % t, type(clone) == type(orig))
    
    #check for equality
    ok("%s: original and unpickled clone have the same UID" % t, orig.get_UID() == clone.get_UID())
    ok("%s: original and unpickled clone have the same mtime" % t, orig.get_mtime() == clone.get_mtime())
    ok("%s: original and unpickled clone have the same hash" % t, orig.get_hash() == clone.get_hash())
    ok("%s: original and unpickled clone have the same rid" % t, orig.get_rid() == clone.get_rid())

finished()
