#common sets up the conduit environment
from common import *

import conduit.Utils as Utils
import conduit.datatypes.File as File

if not is_online() or not is_interactive():
    skip()

#A Reliable file that will note be deleted
SAFE_FILENAME="conduit-icon.png"
SAFE_FILEID=u'75007045'
SAFE_FOLDER="Test"

#setup the test
test = SimpleTest(sourceName="BoxDotNetTwoWay")

boxconfig = {
    "foldername":"Test"
}
test.configure(source=boxconfig)

#get the module directly so we can call some special functions on it
boxdotnet = test.get_source().module

#login
boxdotnet._login()
ok("Login OK", boxdotnet.token != None)

#get the safe folder
folders = boxdotnet._get_folders()
ok("Got expected folder %s" % SAFE_FOLDER, SAFE_FOLDER in folders)

#get the safe file
files = boxdotnet.refresh()
files = boxdotnet.get_all()
ok("Got expected file %s" % SAFE_FILENAME, SAFE_FILEID in files)

#transfer the file to the local disk
tmpdir = Utils.new_tempdir()
f = boxdotnet.get(SAFE_FILEID)
f.transfer(tmpdir)
ok("Transferred file to %s" % tmpdir, f.exists())
ok("Filename retained in transfer", f.get_filename() == SAFE_FILENAME)

#Send a remote file
f = File.File("http://files.conduit-project.org/screenshot.png")
try:
    uid = boxdotnet.put(f, True)
    ok("Upload a file (UID:%s) " % uid, True)
except Exception, err:
    ok("Upload a file (%s)" % err, False)

finished()

