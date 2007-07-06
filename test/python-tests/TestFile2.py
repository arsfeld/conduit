#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.Utils as Utils

import os
import time
import datetime
import gnomevfs
import tempfile

#Tests renaming and setting file mtimes

tmpdir = tempfile.mkdtemp()
ok("Created tempdir %s" % tmpdir, True)

#remote file on readonly location
f = File.File("http://files.conduit-project.org/Conduit-0.1.0-screenshot.png")
ok("Remote file exists", f.exists() == True)

#make another local file
local = Utils.new_tempfile(Utils.random_string())

#save the old information
fOldName = f.get_filename()
fOldSize = f.get_size()
fOldMtime = f.get_mtime()
localOldName = local.get_filename()
localOldSize = local.get_size()
localOldMtime = local.get_mtime()

ok("Got R/O file info (%s)" % fOldName, fOldSize > 0 and fOldMtime != None)
ok("Got file info (%s)" % localOldName, localOldSize > 0 and localOldMtime != None)

#the new filenames
fNewName = Utils.random_string()
localNewName = Utils.random_string()
newDate = datetime.datetime(1983,8,16)

#change the filenames
f.force_new_filename(fNewName)
local.force_new_filename(localNewName)
ok("Renamed R/O file correctly (%s)" % fNewName, fNewName == f.get_filename())
ok("Renamed correctly (%s)" % localNewName, localNewName == local.get_filename())

#change the file mtime
f.force_new_mtime(newDate)
local.force_new_mtime(newDate)
ok("Set mtime R/O file mtime correctly (%s)" % fNewName, f.get_mtime() == newDate)
ok("Set mtime correctly (%s)" % localNewName, local.get_mtime() == newDate)

#transfer to new directory and check that the filenames get withheld in the transfer
f.transfer(tmpdir)
local.transfer(tmpdir)
ok("Transferred R/O file correctly (%s)" % fNewName, f.get_filename() == fNewName)
ok("Transferred correctly (%s)" % localNewName, local.get_filename() == localNewName)

