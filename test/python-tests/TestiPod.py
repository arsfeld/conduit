#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
import conduit.datatypes.Note as Note
import conduit.Utils as Utils

import datetime
import traceback

#Dynamically load all datasources, datasinks and converters
test = SimpleTest()

ipod = None
wrapper = test.get_dataprovider(
                    name="IPodNoteTwoWay",
                    die=False               #dont exit if not found
                    )
if wrapper != None:
    ipod = wrapper.module
else:
    #grossness, simulate an ipod
    from conduit.modules import iPodModule
    fakeIpodDir = os.path.join(os.environ['TEST_DIRECTORY'],"iPod")
    ipod = iPodModule.IPodNoteTwoWay(fakeIpodDir,"")
    ok("Created fake ipod at %s" % ipod.mountPoint, ipod.mountPoint != "")
    if not os.path.exists(fakeIpodDir):
        os.mkdir(fakeIpodDir)

try:
    ipod.refresh()
    ok("Refresh iPod", True)
except Exception, err:
    ok("Refresh iPod (%s)" % err, False) 

#Make a note and save it
newtitle = "Conduit-"+Utils.random_string()
newnote = Note.Note(
                    title=newtitle,
                    contents="Conduit Test Note"
                    )
newnote.set_UID(newtitle)
newnote.set_mtime(datetime.datetime.today())
try:
    rid = ipod.put(newnote,False)
    ok("Put note %s" % newtitle, rid.get_UID() != None)
except Exception, err:
    traceback.print_exc()
    ok("Put note %s" % err, False)

#Check that we saved the note back
ipod.refresh()
ok("Got note", rid.get_UID() in ipod.get_all())

note = ipod.get(rid.get_UID())
comp = note.compare(newnote)
ok("Got note back idenitcal. Comparison %s" % comp, comp == conduit.datatypes.COMPARISON_EQUAL, False)

#check we overwrite the note ok
try:
    newrid = ipod.put(newnote,True,rid.get_UID())
    ok("Overwrite note %s" % newtitle, newrid.get_UID() == rid.get_UID())
except Exception, err:
    ok("Overwrite note %s" % err, False)

#Check that we saved the note back
newnote = ipod.get(newrid.get_UID())
comp = note.compare(newnote)
ok("Got note back idenitcal. Comparison %s" % comp, comp == conduit.datatypes.COMPARISON_EQUAL, False)

finished()
