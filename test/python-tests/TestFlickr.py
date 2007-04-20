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

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)
type_converter = TypeConverter(model)

flickr = model.get_new_module_instance("FlickrSink").module
flickr.username = "%s" % os.environ['TEST_USERNAME']

#A Reliable photo_id of a photo that will not be deleted
SAFE_PHOTO_ID="404284530"

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
f = File.File("http://files.conduit-project.org/Conduit-0.1.0-screenshot.png")
try:
    uid = flickr.put(f, True)
    ok("Upload a photo (UID:%s) " % uid, True)
except Exception, err:
    ok("Upload a photo (%s)" % err, False)

#Upload the photo again
flickr.put(f, True, uid)
ok("Replace the photo (UID:%s) " % uid, True)
#Upload the photo again
flickr.put(f, False, uid)
ok("Skip uploading because photo already uploaded (UID:%s) " % uid, True)
