#common sets up the conduit environment
from common import *

import traceback

import conduit.datatypes.File as File
import conduit.utils as Utils
import conduit.Vfs as Vfs

if not is_online():
    skip()

#A Reliable album name
SAFE_ALBUM_NAME = "Conduit Test"
# Album id of the Conduit test album
SAFE_ALBUM_ID = "2944161"
# Image id of photo in test album
SAFE_IMAGE_ID = "158962651"

#setup the test
test = SimpleTest(sinkName="SmugMugTwoWay")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject"),
    "password":     os.environ["TEST_PASSWORD"],
    "album"   :     SAFE_ALBUM_NAME
}
test.configure(sink=config)

#get the module directly so we can call some special functions on it
smugmug = test.get_sink().module

#Log in
try:
    smugmug.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

# Test getting the album id
album_id = smugmug._get_album_id ()

if album_id:
    ok("Got album id %s for album %s" % (album_id, SAFE_ALBUM_NAME), True)
    if album_id == SAFE_ALBUM_ID:
       ok("Album id %s equals the one we're expecting %s" % (album_id, SAFE_ALBUM_ID), True)
    else:
       ok("Album id %s does not equal the one we're expecting %s" % (album_id, SAFE_ALBUM_ID), False) 
else:
    ok("Didn't succeed in getting an album id...", False)

#Perform image tests
test.do_image_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safePhotoLUID=SAFE_IMAGE_ID
        )

finished()
