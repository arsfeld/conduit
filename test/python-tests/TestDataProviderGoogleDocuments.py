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

docs = google._get_all_documents()
for d in docs:
    print "DOC: %s" % d

doc = google._get_document(d)
#print doc info
info = {"raw txt link":doc.content.src,
        "link":doc.GetAlternateLink().href,
        "title": doc.title.text.encode('UTF-8'),
        "updated":doc.updated.text,
        "author_name":doc.author[0].name.text,
        "author_email":doc.author[0].email.text,
        "type":doc.category[0].label}
for k,v in info.items():
    print "\tINFO %s=%s" % (k,v)
#for c in doc.category:
#    print "CAT: %s" % c.label

path = google._download_doc(info['link'])
print "DL: %s" % path

f = File.File(URI="/home/john/Desktop/test.odt")
LUID = google._upload_document(f)
print "UL: %s" % LUID


finished()
