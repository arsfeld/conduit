#common sets up the conduit environment
from common import *
import conduit.datatypes.File as File

if not is_online():
    skip()

SAFE_DOCID = "http://docs.google.com/feeds/documents/private/full/document%3Adf32bhnd_2dv44zrfc"

test = SimpleTest(sinkName="DocumentsSink")
config = {
    "username":     os.environ.get("TEST_USERNAME","conduitproject@gmail.com"),
    "password":     os.environ["TEST_PASSWORD"],
}
test.configure(sink=config)
google = test.get_sink().module

#Log in
try:
    google.refresh()
    ok("Logged in", google.loggedIn == True)
except Exception, err:
    ok("Logged in (%s)" % err, False) 

docs = google.get_all()
num = len(docs)
ok("Got %s documents" % num, num > 0)

doc = google._get_document(SAFE_DOCID)
ok("Got safe document", doc != None)

f = File.File(URI=get_external_resources("file")["doc"])
test.do_dataprovider_tests(
        supportsGet=False,
        supportsDelete=True,
        safeLUID=SAFE_DOCID,
        data=f,
        name="file"
        )


finished()

