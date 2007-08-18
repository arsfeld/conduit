#common sets up the conduit environment
from common import *

import traceback
import gnomevfs

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.Utils as Utils

if not is_online():
    print "SKIPPING"
    sys.exit()

#A Reliable photo_id of a photo that will not be deleted
SAFE_PHOTO_ID="404284530"

#setup the test
test = SimpleTest(sinkName="FlickrSink")
config = {
    "username":     os.environ['TEST_USERNAME'],
    "tagWith" :     "Conduit",
    "showPublic":   False
}
test.configure(sink=config)

#get the module directly so we can call some special functions on it
flickr = test.get_sink().module

#Log in
try:
    flickr.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

#Get user quota
used,tot = flickr._get_user_quota()
p = (float(used)/float(tot))*100.0
ok("Used %2.1f%% of monthly badwidth quota (%skb/%skb)" % (p,used,tot) , used != -1 and tot != -1)

#Test getting the info and URL of a photo
info = flickr._get_photo_info(SAFE_PHOTO_ID)
ok("Got photo info", info != None)
url = flickr._get_raw_photo_url(info)
ok("Got photo url (%s)" % url, url != None)
ok("Photo url is correct", gnomevfs.exists(gnomevfs.URI(url)))

#Send a remote file
f = File.File("http://files.conduit-project.org/screenshot.png")
try:
    uid = flickr.put(f, True)
    ok("Upload a photo (UID:%s) " % uid, True)
except Exception, err:
    ok("Upload a photo (%s)" % err, False)

