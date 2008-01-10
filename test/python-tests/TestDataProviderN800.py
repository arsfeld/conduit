#common sets up the conduit environment
from common import *

import traceback

import conduit.modules.N800Module.N800Module as N800Module

#simulate a n800
fakeN800Dir = os.path.join(os.environ['TEST_DIRECTORY'],"n800")
if not os.path.exists(fakeN800Dir):
    os.mkdir(fakeN800Dir)
ok("Created fake n800 at %s" % fakeN800Dir, os.path.exists(fakeN800Dir))

n800FolderDp = N800Module.N800FolderTwoWay(fakeN800Dir,"")

TESTS = (
#dpinstance,        #newdata_func,          #name
(n800FolderDp,      new_file,               "N800FolderTwoWay"),
)

for dp, newdata_func, name in TESTS:
    try:
        dp.refresh()
        ok("%s: Refresh" % name, True)
    except Exception, err:
        ok("%s: Refresh (%s)" % (name,err), False) 

    #Make data and put it
    newdata = newdata_func(None)
    newtitle = newdata.get_UID()
        
    try:
        rid = dp.put(newdata,False)
        ok("%s: Put %s" % (name, newtitle), rid.get_UID() != None)
    except Exception, err:
        traceback.print_exc()
        ok("%s: Put %s" % (name, err), False)

    #Check that we saved the note back
    dp.refresh()
    ok("%s: Got all (%s in %s)" % (name,rid.get_UID(),dp.get_all()), rid.get_UID() in dp.get_all())

    data = dp.get(rid.get_UID())
    comp = data.compare(newdata)
    ok("%s: Got back idenitcal. Comparison %s" % (name, comp), comp == conduit.datatypes.COMPARISON_EQUAL, False)

    #check we overwrite the data ok
    try:
        newrid = dp.put(newdata,True,rid.get_UID())
        ok("%s: Overwrite %s" % (name, newtitle), newrid.get_UID() == rid.get_UID())
    except Exception, err:
        ok("%s: Overwrite %s" % (name, err), False)

    #Check that we saved the data back
    newdata = dp.get(newrid.get_UID())
    comp = data.compare(newdata)
    ok("%s: Got back idenitcal. Comparison %s" % (name, comp), comp == conduit.datatypes.COMPARISON_EQUAL, False)

finished()
