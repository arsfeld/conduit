#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.Contact as Contact

import traceback

#get a list of all vcard files
vcards = get_files_from_data_dir("*.vcard")

try:
    f = Contact.Contact()
except:
    ok("Must specify URI", True)

for i in vcards:
    try:
        c = Contact.Contact(i)
        ok("Created contact from file %s" % i, True)
        c.set_from_vcard_string( read_data_file(i) )

        #check the URI
        ok("Uri (%s) retained" % os.path.basename(i), c.get_open_URI() == i)

    except:
        ok("Created contact from file %s\n%s" % (i,traceback.format_exc()), False, False)

    
