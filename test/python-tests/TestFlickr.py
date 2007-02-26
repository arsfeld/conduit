#common sets up the conduit environment
from common import *

import traceback

from conduit.Module import ModuleManager
from conduit.TypeConverter import TypeConverter
import conduit.datatypes.Email as Email
import conduit.datatypes.File as File
import conduit.Utils as Utils

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)
type_converter = TypeConverter(model)

flickr = model.get_new_module_instance("FlickrSink").module
flickr.username = "%s" % os.environ['TEST_USERNAME']

#Log in
try:
    flickr.refresh()
    ok("Logged in", True)
except Exception, err:
    ok("Logged in (%s)" % err, False)  

#Send a remote file
f = File.File("http://files.conduit-project.org/Conduit-0.1.0-screenshot.png")

try:
    uid = flickr.put(f, True)
    ok("Upload a photo (UID:%s) " % uid, True)
except Exception, err:
    traceback.print_exc()
    ok("Upload a photo (%s)" % err, False)
    

