import os
import glob

#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.Contact as Contact

#get a list of all vcard files
vcards = get_files_from_data_dir("*.vcard")

try:
    f = Contact.Contact()
except:
    ok("Must specify URI", True)

for i in vcards:
    c = Contact.Contact(i)
    f = open(i,'r')
    c.set_from_vcard_string(f.read())
    f.close()

    #check the URI
    ok("Uri (%s) retained" % os.path.basename(i),c.get_open_URI() == i)
    
