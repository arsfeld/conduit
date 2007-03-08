#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
import conduit.datatypes.Note as Note
import conduit.Utils as Utils

import datetime

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)

ipod = None
#look for an ipod
for i in model.get_all_modules():
    if i.classname == "IPodNoteTwoWay":
        ipod = model.get_new_module_instance(i.get_key()).module

if ipod != None:
    ok("Detected iPod", True)
else:
    #grossness, simulate an ipod
    from conduit.dataproviders import iPodModule
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
                    mtime=datetime.datetime.today(),
                    contents="Conduit Test Note",
                    raw="RAW Conduit Test Note"
                    )
try:
    newuid = ipod.put(newnote,False)
    ok("Put note %s" % newtitle, newtitle == newuid)
except Exception, err:
    ok("Put note %s" % err, False)

#check we overwrite the note ok
try:
    newnewuid = ipod.put(newnote,True,newuid)
    ok("Overwrite note %s" % newtitle, newnewuid == newuid)
except Exception, err:
    ok("Overwrite note %s" % err, False)


#Check that we saved the note back
note = ipod._get_note_from_ipod(newuid)
comp = note.compare(newnote)
ok("Got note back idenitcal. Comparison %s" % comp, comp == conduit.datatypes.COMPARISON_EQUAL)

#Check that we saved the note back
try:
    ipod.refresh()
    num = ipod.get_num_items()
    ok("Notes Present on iPod %s" % num, num>0)
except Exception, err:
    ok("Could not get number of notes on ipod (%s)" % err, False) 

