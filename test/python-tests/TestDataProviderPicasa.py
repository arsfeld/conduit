#common sets up the conduit environment
from common import *

import traceback

import conduit.datatypes.File as File
import conduit.Vfs as Vfs

if not is_online():
    skip()

#A Reliable album name
SAFE_ALBUM_NAME = "Conduit Test"
# Album id of the Conduit test album
SAFE_ALBUM_ID = "5073563135802702689"
# Image id of photo in test album
SAFE_PHOTO_ID = "5073564926804065138"

#setup the test
test = SimpleTest(sinkName="PicasaTwoWay")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject"),
    "password":     os.environ["TEST_PASSWORD"],
    "album"   :     SAFE_ALBUM_NAME
}
test.configure(sink=config)

#get the module directly so we can call some special functions on it
picasa = test.get_sink().module

#Log in
try:
    picasa.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)

# Album tests:
# Loaded?
ok("Loaded album", picasa.galbum != None)

# Correct name?
if picasa.galbum.name == SAFE_ALBUM_NAME:
    ok("Album name is ok: expected '%s', received '%s'" % (SAFE_ALBUM_NAME, picasa.galbum.name), True)
else:
    ok("Album name is not ok: expected '%s', received '%s'" % (SAFE_ALBUM_NAME, picasa.galbum.name), False)

# Expected id?
if picasa.galbum.id == SAFE_ALBUM_ID:
    ok("Album equals the one we're expecting: %s" % SAFE_ALBUM_ID, True)
else:
    ok("Album has an unexpected id: %s instead of %s" % (picasa.galbum.id, SAFE_ALBUM_ID), False)

#Perform image tests
test.do_image_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safePhotoLUID=SAFE_PHOTO_ID
        )

finished()
