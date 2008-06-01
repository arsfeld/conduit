#common sets up the conduit environment
from common import *

if not is_online():
    skip()

#A Reliable album name
SAFE_ALBUM_NAME = "test"
# Album id of the Conduit test album
SAFE_ALBUM_ID = 15860
# Image id of photo in test album
SAFE_PHOTO_ID = '6fd9a52fbb14c4e044b5a6c5de956b7e'

#setup the test
test = SimpleTest(sinkName="ZotoSink")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject"),
    "password":     os.environ["TEST_PASSWORD"],
    "albumName"   :     SAFE_ALBUM_NAME
}

test.configure(sink=config)

#get the module directly so we can call some special functions on it
zoto = test.get_sink().module

#Log in
try:
    zoto.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

# Test getting the album id
if not zoto.albumId:
    ok("Didn't succeed in getting an album id...", False)

album_id = zoto.albumId

if album_id:
    ok("Got album id %s for album %s" % (album_id, SAFE_ALBUM_NAME), True)
    if album_id == SAFE_ALBUM_ID:
       ok("Album id %s equals the one we're expecting %s" % (album_id, SAFE_ALBUM_ID), True)
    else:
       ok("Album id %s does not equal the one we're expecting %s" % (album_id, SAFE_ALBUM_ID), False) 

#Perform image tests
test.do_image_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safePhotoLUID=SAFE_PHOTO_ID,
        ext="jpg"
        )

finished()
