#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)

tomboy = model.get_new_module_instance("TomboyNoteTwoWay").module

try:
    tomboy.refresh()
    ok("Refresh Tomboy", True)
except Exception, err:
    ok("Refresh Tomboy (%s)" % err, False) 

num = tomboy.get_num_items()
ok("Got all notes (%s)" % num, num > 1)
