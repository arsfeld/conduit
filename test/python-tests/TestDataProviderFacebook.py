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

#Perform image tests
#test.do_image_dataprovider_tests(
#        supportsGet=False,
#        supportsDelete=False,
#        safePhotoLUID=None
#        )

#Send a remote file
f = Photo.Photo(URI="http://files.conduit-project.org/screenshot.png")
try:
    rid = facebook.put(f, True)
    ok("Upload a photo (%s) " % rid, True)
except Exception, err:
    ok("Upload a photo (%s)" % err, False)

finished()

