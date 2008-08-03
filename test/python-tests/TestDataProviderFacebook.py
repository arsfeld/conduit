#common sets up the conduit environment
from common import *

if not is_online() or not is_interactive():
    skip()

#setup the test
test = SimpleTest(sinkName="FacebookSink")
#Hack Facebook to use the system browser (it really needs to use the gtkmozembed one)
facebook = test.get_sink().module
facebook.browser = "system"

#Log in
try:
    facebook.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)
    
albums = facebook._get_albums()
ok("Got %d albums" % len(albums), len(albums) > 0)

aid = albums['Conduit Photos']
photos = facebook._get_photos(int(aid))
ok("Got %d photos" % len(photos), len(photos) > 0)

#Perform image tests
test.do_image_dataprovider_tests(
        supportsGet=False,
        supportsDelete=False,
        safePhotoLUID=None
        )

finished()

