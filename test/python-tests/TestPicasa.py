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
SAFE_ALBUM_ID = "5073563135802702689"
# Image id of photo in test album
SAFE_PHOTO_ID = "5073564926804065138"

#setup the test
test = SimpleTest(sinkName="PicasaSink")
config = {
    "username":     os.environ['TEST_USERNAME'],
    "password":     os.environ['TEST_PASSWORD'],
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

# Photo tests:
# Loaded?
ok("Loaded photos", picasa.gphotos != None)

# Expected photo available?
ok("Expected image available", picasa.gphotos.has_key (SAFE_PHOTO_ID))

# Get info
info = picasa._get_photo_info (SAFE_PHOTO_ID)
ok("Got photo info", info != None)

# Get url
url = picasa._get_raw_photo_url (info)
ok ("Got photo url %s" % url, url != None)
ok ("Photo url is correct", gnomevfs.exists (gnomevfs.URI(url)))

# TODO: find a jpeg to upload    
 #Send a remote file
# f = File.File("http://files.conduit-project.org/Conduit-0.1.0-screenshot.png")
# try:
#     uid = picasa.put(f, True)
#     ok("Upload a photo (UID:%s) " % uid, True)
# except Exception, err:
#     ok("Upload a photo (%s)" % err, False)

