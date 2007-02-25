import os
import glob

#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.Event as Event

#get a list of all vcard files
icals = get_files_from_data_dir("*.ical")

try:
    f = Event.Event()
except:
    ok("Must specify URI", True)

for i in icals:
    c = Event.Event(i)
    f = open(i,'r')
    c.set_from_ical_string(f.read())
    f.close()

    #check the URI
    ok("Uri (%s) retained" % os.path.basename(i),c.get_open_URI() == i)
