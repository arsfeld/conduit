#common sets up the conduit environment
from common import *

import traceback
import gnomevfs

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.File as File
import conduit.Utils as Utils

if not is_online():
    print "SKIPPING"
    sys.exit()

#A Reliable album name
SAFE_ALBUM_NAME = "Conduit Test"
# Album id of the Conduit test album
SAFE_ALBUM_ID = '2944161'
# Image id of photo in test album
SAFE_IMAGE_ID = '158962651'

#setup the test
test = SimpleTest(sinkName="SmugMugSink")
config = {
    "username":     os.environ['TEST_USERNAME'],
    "password":     os.environ['TEST_PASSWORD'],
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

# Test getting photo info and url
info = smugmug._get_photo_info (SAFE_IMAGE_ID)
ok("Got photo info", info != None)

url = smugmug._get_raw_photo_url (info)
ok ("Got photo url %s" % url, url != None)
ok ("Photo url is correct", gnomevfs.exists (gnomevfs.URI(url)))
   
#Send a remote file
f = File.File("http://files.conduit-project.org/screenshot.png")
uid = None
try:
    uid = smugmug.put(f, True)
    ok("Upload a photo (UID:%s) " % uid, True)
except Exception, err:
    ok("Upload a photo (%s)" % err, False)

# try delete if upload succeeded
if uid:
    try:
        smugmug.delete(uid)
        ok("Delete succeeded", True)
    except Exception, err:
        ok("Delete failed %s" % err, False)

    
