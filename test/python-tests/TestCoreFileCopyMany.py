#common sets up the conduit environment
from common import *

import conduit.Vfs as Vfs
import conduit.utils as Utils
import conduit.datatypes.File as File

import time
import os.path

#Get a giant list of many music files
music = open(
            os.path.join(get_data_dir(), "music-list.txt"),
            "r")

sourceDir = Utils.new_tempdir()
sinkDir = Utils.new_tempdir()
lines = [Vfs.uri_join(sourceDir, l[0:-1]) for l in music]
dirs = {}

for l in lines:
    dirs[os.path.dirname(l)] = True

#make all the directories for these files
for d in dirs:  
    f = File.File(d)
    f.make_directory_and_parents()

#leaving only files behind
for d in dirs:
    try:
        lines.remove(d)
    except ValueError: pass

for music in lines:
    f = File.File(music)
    f.set_contents_as_text("1")

#Copy all files to destination
dest = File.File(sinkDir)
for music in lines:
    dest = Vfs.uri_join(
                sinkDir,
                Vfs.uri_get_relative(sourceDir, music))

    xfer = Vfs.FileTransfer(
                    File.File(music)._get_impl(),
                    dest)
    i = xfer.transfer(False, None)[0]
    if not i:
        ok("File transfer failed", i)

def prog(*args): pass
def done(*args): pass

stm = Vfs.FolderScannerThreadManager(maxConcurrentThreads=1)
t1 = stm.make_thread(sourceDir, True, True, prog, done)
t2 = stm.make_thread(sinkDir, True, True, prog, done)
stm.join_all_threads()

uris1 = t1.get_uris()
uris2 = t2.get_uris()

ok("%d files copied from %s (%d files) -> %s (%d files)" % (
            len(lines),sourceDir,len(uris1),sinkDir,len(uris2)),
            len(lines) == len(uris1) == len(uris2)
            )

finished()


