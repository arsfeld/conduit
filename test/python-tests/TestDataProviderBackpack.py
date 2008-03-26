#common sets up the conduit environment
from common import *

import traceback
import datetime

import conduit.datatypes.Note as Note
import conduit.utils as Utils

if not is_online():
    skip()

#setup the test
test = SimpleTest(sinkName="BackpackNoteSink")
config = {
    "username" :        os.environ.get("TEST_USERNAME","conduitproject"),
    "apikey" :          "13f3e8657d25d399f4b6b4f7eda7986ae6e0fbde",
    "storeInPage" :     "Test"
}    
test.configure(sink=config)

#get the module directly so we can call some special functions on it
backpack = test.get_sink().module

#The ID of the Test page
SAFE_PAGEID=1352096
#A Reliable note that will note be deleted
SAFE_FILEID=2575890

#Log in
try:
    backpack.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

#get the safe folder
ok("Got page %s" % SAFE_PAGEID, SAFE_PAGEID == backpack.pageID)

#Perform basic tests
n = Note.Note(
            title=Utils.random_string(),
            modified=datetime.datetime.today(),
            contents="Random Note\n* list"
            )
test.do_dataprovider_tests(
        supportsGet=True,
        supportsDelete=True,
        safeLUID=SAFE_FILEID,
        data=n,
        name="note"
        )

finished()
