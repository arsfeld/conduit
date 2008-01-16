#common sets up the conduit environment
from common import *

import traceback
import datetime

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.Note as Note
import conduit.Utils as Utils

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

#Log in
try:
    backpack.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

#Add a note
title = Utils.random_string()
mtime = datetime.datetime.today()
n = Note.Note(
            title=title,
            modified=mtime,
            contents="Test Note 1\n* list"
            )
try:
    rid = backpack.put(n, True)
    ok("Add a note (%s)" % rid, True)
except Exception, err:
    traceback.print_exc()
    ok("Add a note (%s)" % err, False)

#Add another note
n = Note.Note(
            title=Utils.random_string(),
            modified=datetime.datetime.today(),
            contents="Test Note 2"
            )
try:
    rid = backpack.put(n, True)
    uid = rid.get_UID()
    ok("Add another note (%s)" % rid, True)
except Exception, err:
    traceback.print_exc()
    ok("Add another note (%s)" % err, False)

#now update that note
n.contents = "Updated Note"
try:
    rid = backpack.put(n, True, uid)
    ok("Update a note (%s)" % rid, True)
except Exception, err:
    traceback.print_exc()
    ok("Update a note (%s)" % err, False)
    
try:
    backpack.refresh()
    backpack.delete(uid)
    backpack.refresh()
    ok("Delete a note (%s)" % rid, uid not in backpack.get_all())
except Exception, err:
    traceback.print_exc()
    ok("Delete a note (%s)" % err, False)
    
finished()
