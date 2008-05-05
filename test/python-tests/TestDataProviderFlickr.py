#common sets up the conduit environment
from common import *

#Flickr is non-interactive once you have got a frob for the first time
if not is_online():
    skip()

#A Reliable photo_id of a photo that will not be deleted
SAFE_PHOTO_ID="404284530"

#setup the test
test = SimpleTest(sinkName="FlickrTwoWay")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject"),
    "photoSetName": "Conduit",
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
used,tot,percent = flickr._get_user_quota()
ok("Used %2.1f%% of monthly badwidth quota (%skb/%skb)" % (percent,used,tot) , used != -1 and tot != -1)

#Perform image tests
test.do_image_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safePhotoLUID=SAFE_PHOTO_ID
        )

finished()
