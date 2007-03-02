#common sets up the conduit environment
from common import *

from conduit.Module import ModuleManager

#Dynamically load all datasources, datasinks and converters
dirs_to_search =    [
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
model = ModuleManager(dirs_to_search)

ipod = None
#look for an ipod
for i in model.get_all_modules():
    if i.classname == "IPodNoteTwoWay":
        ipod = model.get_new_module_instance(i.get_key()).module

ok("Detected iPod", ipod != None)

try:
    ipod.refresh()
    ok("Refresh iPod", True)
except Exception, err:
    ok("Refresh iPod (%s)" % err, False) 
