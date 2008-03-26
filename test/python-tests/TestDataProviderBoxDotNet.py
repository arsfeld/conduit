#common sets up the conduit environment
from common import *

import traceback

import conduit.utils as Utils
import conduit.datatypes.File as File

if not is_online() or not is_interactive():
    skip()

#A Reliable file that will note be deleted
SAFE_FILENAME="conduit.png"
SAFE_FILEID=u'124531811'
SAFE_FOLDER="Test"

#setup the test
test = SimpleTest(sinkName="BoxDotNetTwoWay")
boxconfig = {
    "foldername":"Test"
}
test.configure(sink=boxconfig)

#get the module directly so we can call some special functions on it
boxdotnet = test.get_sink().module

#Log in
try:
    boxdotnet.refresh()
    ok("Logged in", boxdotnet.token != None)
except Exception, err:
    ok("Logged in (%s)" % err, False) 

#get the safe folder
folders = boxdotnet._get_folders()
ok("Got expected folder %s" % SAFE_FOLDER, SAFE_FOLDER in folders)

#Perform basic tests
f = new_file(None)
test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safeLUID=SAFE_FILEID,
        data=f,
        name="file"
        )

finished()

