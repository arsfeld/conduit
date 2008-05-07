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

print google._get_all_documents()

#f = File.File(URI="/home/john/Desktop/test2.odt")
#print google._upload_document(f)

#print google._get_document("http://docs.google.com/feeds/documents/private/full/document%3Adf32bhnd_6dvqk4x2f")

google._download_doc('df32bhnd_6dvqk4x2f')

finished()
