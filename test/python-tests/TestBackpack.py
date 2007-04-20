#common sets up the conduit environment
from common import *

import traceback
import datetime

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.Note as Note
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

backpack = model.get_new_module_instance("BackpackNoteSink").module
backpack.username = "%s" % os.environ['TEST_USERNAME']
#This key is meant to be secret, but it doesnt really matter because this account
#is solely for testing
backpack.apikey = "13f3e8657d25d399f4b6b4f7eda7986ae6e0fbde"
backpack.storeInPage = "%s-%s" % (conduit.APPNAME, conduit.APPVERSION)

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
            contents="This is a test note \n* list\n*list"
            )
try:
    uid = backpack.put(n, True)
    ok("Add a note (UID:%s)" % uid, True)
except Exception, err:
    traceback.print_exc()
    ok("Add a note (%s)" % err, False)

#Add another note
title = Utils.random_string()
mtime = datetime.datetime.today()
n = Note.Note(
            title=title,
            modified=mtime,
            contents="Test Note\n* list\n* list"
            )
try:
    uid = backpack.put(n, True)
    ok("Add a note (UID:%s)" % uid, True)
except Exception, err:
    traceback.print_exc()
    ok("Add a note (%s)" % err, False)

#now update that note
n.contents = "Updated Note"
try:
    uid = backpack.put(n, True)
    ok("Update a note (UID:%s)" % uid, True)
except Exception, err:
    traceback.print_exc()
    ok("Update a note (%s)" % err, False)
