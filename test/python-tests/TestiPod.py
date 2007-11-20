#common sets up the conduit environment
from common import *

import datetime
import traceback

import conduit.datatypes.Note as Note
import conduit.Utils as Utils
import conduit.modules.iPodModule as iPodModule

#grossness, simulate an ipod
fakeIpodDir = os.path.join(os.environ['TEST_DIRECTORY'],"iPod")
if not os.path.exists(fakeIpodDir):
    os.mkdir(fakeIpodDir)
ok("Created fake ipod at %s" % fakeIpodDir, os.path.exists(fakeIpodDir))

ipodNoteDp = iPodModule.IPodNoteTwoWay(fakeIpodDir,"")

TESTS = (
#dpinstance,        #newdata_func,          #name
(ipodNoteDp,        new_note,               "note"),
)

for ipod, newdata_func, name in TESTS:
    try:
        ipod.refresh()
        ok("iPod %s: Refresh" % name, True)
    except Exception, err:
        ok("iPod %s: Refresh (%s)" % (name,err), False) 

    #Make a note and save it
    newnote = newdata_func("")
    newtitle = newnote.get_UID()
        
    try:
        rid = ipod.put(newnote,False)
        ok("iPod %s: Put %s" % (name, newtitle), rid.get_UID() != None)
    except Exception, err:
        traceback.print_exc()
        ok("iPod %s: Put %s" % (name, err), False)

    #Check that we saved the note back
    ipod.refresh()
    ok("iPod %s: Got all" % name, rid.get_UID() in ipod.get_all())

    note = ipod.get(rid.get_UID())
    comp = note.compare(newnote)
    ok("iPod %s: Got back idenitcal. Comparison %s" % (name, comp), comp == conduit.datatypes.COMPARISON_EQUAL, False)

    #check we overwrite the note ok
    try:
        newrid = ipod.put(newnote,True,rid.get_UID())
        ok("iPod %s: Overwrite %s" % (name, newtitle), newrid.get_UID() == rid.get_UID())
    except Exception, err:
        ok("iPod %s: Overwrite %s" % (name, err), False)

    #Check that we saved the note back
    newnote = ipod.get(newrid.get_UID())
    comp = note.compare(newnote)
    ok("iPod %s: Got back idenitcal. Comparison %s" % (name, comp), comp == conduit.datatypes.COMPARISON_EQUAL, False)

finished()
