#common sets up the conduit environment
from common import *
import conduit.datatypes.File as File

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

doc = google._get_document(docs[-1])
ok("Got safe document", doc != None)



#finished()



#path = google._download_doc(info['link'])
#print "DL: %s" % path

f = File.File(URI="/home/john/Desktop/test.ppt")
LUID = google._upload_document(f)
doc = google._get_document(LUID)

ok("Upload document: %s" % doc, doc != None)

path = google._download_doc(doc)
print path

finished()
