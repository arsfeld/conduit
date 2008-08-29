#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.File as File
import conduit.utils as Utils

if not is_online():
    skip()

#A Reliable album name
SAFE_ALBUM_NAME = "Conduit Screenshots"
# Album id of the Conduit test album
SAFE_ALBUM_ID = '67b0de21b3f166ce845f'
# Image id of photo in test album
SAFE_PHOTO_ID = '47b7cf26b3127cceb04728a35c2600000020100AZOGbJw2buGKg'

#setup the test
test = SimpleTest(sinkName="ShutterflySink")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject@gmail.com"),
    "password":     os.environ["TEST_PASSWORD"],
    "album"   :     SAFE_ALBUM_NAME
}
test.configure(sink=config)

#get the module directly so we can call some special functions on it
shutter = test.get_sink().module

#Log in
try:
    shutter.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

# Test getting the album id
if not shutter.salbum:
    ok("Didn't succeed in getting an album id...", False)

album_id = shutter.salbum.id    

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

