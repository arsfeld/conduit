#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.Utils as Utils

import time
import datetime
import gnomevfs
import tempfile

tmpdir = tempfile.mkdtemp()
ok("Created tempdir %s" % tmpdir, True)

f = File.File("http://files.conduit-project.org/Conduit-0.1.0-screenshot.png")
ok("Remote file exists", f.exists() == True)

#make another local file
local = Utils.new_tempfile(Utils.random_string())

#save the old information
fOldName = f._get_text_uri()
fOldSize = f.get_size()
fOldMtime = f.get_mtime()
localOldName = local._get_text_uri()
localOldSize = local.get_size()
localOldMtime = local.get_mtime()

ok("Got old file info (%s)" % fOldName, fOldSize > 0 and fOldMtime != None)
ok("Got old file info (%s)" % localOldName, localOldSize > 0 and localOldMtime != None)

#the new filenames
fNewName = Utils.random_string()
localNewName = Utils.random_string()
newDate = datetime.datetime(1983,8,16)

#transfer the files
f.transfer(os.path.join(tmpdir,fNewName))
local.transfer(os.path.join(tmpdir,localNewName))

#change the file mtime
f.force_new_mtime(newDate)
local.force_new_mtime(newDate)

ok("Transferred correctly (%s)" % fNewName, f.get_filename() == fNewName)
ok("Transferred correctly (%s)" % localNewName, local.get_filename() == localNewName)

ok("Set mtime correctly (%s)" % fNewName, f.get_mtime() == newDate)
ok("Set mtime correctly (%s)" % localNewName, local.get_mtime() == newDate)

#rename
fNewNewName = Utils.random_string()
localNewNewName = Utils.random_string()
f.force_new_filename(fNewNewName)
local.force_new_filename(localNewNewName)

ok("Renamed correctly (%s)" % fNewNewName, f.get_filename() == fNewNewName)
ok("Renamed correctly (%s)" % localNewNewName, local.get_filename() == localNewNewName)

