#common sets up the conduit environment
from common import *

if not is_online() or not is_interactive():
    skip()

#setup the test
test = SimpleTest(sinkName="FacebookSink")
#Hack Facebook to use the system browser (it really needs to use the gtkmozembed one)
facebook = test.get_dataprovider("FacebookSink").module
facebook.browser = "system"

#Log in
try:
    facebook.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

#Send a remote file
f = File.File("http://files.conduit-project.org/screenshot.png")
try:
    uid = facebook.put(f, True)
    ok("Upload a photo (UID:%s) " % uid, True)
except Exception, err:
    ok("Upload a photo (%s)" % err, False)

finished()

