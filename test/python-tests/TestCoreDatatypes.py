#common sets up the conduit environment
from common import *

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
    }

for t,func in TYPES.items():
    dat = func(None)
    ok("%s: Created new instance" % t, dat != None)
    ok("%s: get_UID() implemented" % t, dat.get_UID() != None)
    ok("%s: get_rid() works" % t, dat.get_rid() != None)
finished()
