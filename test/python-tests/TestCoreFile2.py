#common sets up the conduit environment
from common import *

import conduit
import conduit.datatypes.File as File
import conduit.utils as Utils

import os
import time
import datetime
import gnomevfs
import tempfile

if not is_online():
    skip()

tmpdir = tempfile.mkdtemp()
ok("Created tempdir %s" % tmpdir, True)

#remote file on readonly location
f = File.File("http://files.conduit-project.org/screenshot.png")
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

#play with proxy files, i.e. files that are like remote files, but stop being such
#when transferred to the local system
day0 = datetime.datetime(1983,8,16)
day1 = datetime.datetime(1983,8,17)

#compare two proxy files based on mtime only
f = File.ProxyFile(
            URI=get_external_resources("file")["remote"],
            name=None,
            modified=day0,
            size=None)
f2 = File.ProxyFile(
            URI=get_external_resources("file")["remote"],
            name=None,
            modified=day1,
            size=None)
comp = f.compare(f2)
ok("Proxy file comparison (mtime): %s" % comp,comp == conduit.datatypes.COMPARISON_OLDER)

#compare two proxy files based on size only
proxyFileName = Utils.random_string()
f = File.ProxyFile(
            URI=get_external_resources("file")["remote"],
            name=None,
            modified=day0,
            size=10)
f2 = File.ProxyFile(
            URI=get_external_resources("file")["remote"],
            name=proxyFileName,
            modified=day0,
            size=10)
comp = f.compare(f2)
ok("Proxy file comparison (size): %s" % comp,comp == conduit.datatypes.COMPARISON_EQUAL)

f2.transfer(tmpdir)
ok("Transferred ProxyFile correctly (%s)" % proxyFileName, f2.get_filename() == proxyFileName)

ok("ProxyFile graduated to real file", f2._is_proxyfile() == False)
            
finished()
