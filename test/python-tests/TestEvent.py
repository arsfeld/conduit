#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.Event as Event

import traceback

#get a list of all vcard files
icals = get_files_from_data_dir("*.ical")

try:
    f = Event.Event()
except:
    ok("Must specify URI", True)

for i in icals:
    try:
        c = Event.Event(i)
        ok("Created event from file %s" % i, True)
        c.set_from_ical_string( read_data_file(i) )

        #check the URI
        ok("Uri (%s) retained" % os.path.basename(i), c.get_open_URI() == i)

    except:
        ok("Created event from file %s\n%s" % (i,traceback.format_exc()), False, False)

