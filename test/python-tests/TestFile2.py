#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.Utils as Utils

f = File.File("ssh://root@www.greenbirdsystems.com/root/sync/Image.png")
ok("Remote file exists", f.exists() == True)

local = f.get_local_uri()
ok("Getting local copy of a remote file = %s" % local,type(local) == str and len(local) > 0)

import gnomevfs

#change some file info
info = gnomevfs.FileInfo()
info.name = Utils.random_string()

#rename the file
uri = gnomevfs.URI(local)

try:
    gnomevfs.set_file_info(uri, info, gnomevfs.SET_FILE_INFO_NAME)
    ok("Rename file (new name:%s)" % info.name, True)
except Exception, err:
    ok("Rename file (%s)" % err, False)

try:
    gnomevfs.set_file_info(uri, info, gnomevfs.SET_FILE_INFO_NAME)
    ok("Rename to existing file", False)
except gnomevfs.FileExistsError:
    #should fail
    ok("Rename to existing file", True)
