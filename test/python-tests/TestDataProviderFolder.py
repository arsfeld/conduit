#common sets up the conduit environment
from common import *

import conduit.dataproviders.File as FileDataProvider
import conduit.datatypes.File as File
import conduit.utils as Utils
import conduit.Vfs as Vfs

GROUP_NAME = "Cheese"
NESTED_DIR_NAME = "A Directory"
DIFFERENT_GROUP_NAME = "Steak"

def create_file(inDirURI):
    name = Utils.random_string()+".txt"
    uri = Vfs.uri_join(inDirURI.replace("file://",""),name)
    f = open(uri,'w')
    f.write(Utils.random_string())
    f.close()
    return name,uri

#Test removable volume support
removableUri = get_external_resources('folder')['removable-volume']
ok("Is on a removable volume", FileDataProvider.is_on_removable_volume(removableUri))

#save and restore a group
groupInfo = (removableUri, GROUP_NAME)
ok("Save group info", FileDataProvider.save_removable_volume_group_file(*groupInfo))
readInfo = FileDataProvider.read_removable_volume_group_file(removableUri)
ok("Read group info (%s)" % str(readInfo), len(readInfo) > 0 and readInfo[0][1] == GROUP_NAME)

#create some test directories
dpdir = "file://"+Utils.new_tempdir()
tempdir = "file://"+Utils.new_tempdir()
tempdir2 = Vfs.uri_join(tempdir, NESTED_DIR_NAME)
Vfs.uri_make_directory(tempdir2)
#create some test files
f1Name, f1URI = create_file(tempdir)
f2Name, f2URI = create_file(tempdir2)
#create a test dataprovider
dp = FileDataProvider.FolderTwoWay(
            folder=dpdir,
            folderGroupName=GROUP_NAME,
            includeHidden=False,
            compareIgnoreMtime=False,
            followSymlinks=False)

# Scenario 1)
#   File came from a foreign DP like tomboy. No concept of relative path
#   or group. Goes into the folder and keeps its name
plainFile = Utils.new_tempfile("TomboyNote")
plainFileName = plainFile.get_filename()
rid = dp.put(
        vfsFile=plainFile,
        overwrite=False,
        LUID=None)
ok("Put plain file", rid.get_UID() == Vfs.uri_join(dpdir,plainFileName))

# Scehario 2a)
#   File came from another folder dp with the same group
#   Goes into the folder, keeps its relative path
f1 = File.File(
        URI=f1URI,
        basepath=tempdir,
        group=GROUP_NAME)
rid = dp.put(
        vfsFile=f1,
        overwrite=False,
        LUID=None)
ok("Put same group file", rid.get_UID() == Vfs.uri_join(dpdir,f1Name))

f2 = File.File(
        URI=f2URI,
        basepath=tempdir,
        group=GROUP_NAME)
rid = dp.put(
        vfsFile=f2,
        overwrite=False,
        LUID=None)
ok("Put same group file in nested dir", rid.get_UID() == Vfs.uri_join(dpdir,NESTED_DIR_NAME,f2Name))

# Scehario 2b)
#   File came from another folder dp with a different group
#   Goes into a new folder, by the name of the group, keeps its relative path
f1 = File.File(
        URI=f1URI,
        basepath=tempdir,
        group=DIFFERENT_GROUP_NAME)
rid = dp.put(
        vfsFile=f1,
        overwrite=False,
        LUID=None)
ok("Put different group file", rid.get_UID() == Vfs.uri_join(dpdir,DIFFERENT_GROUP_NAME,f1Name))

f2 = File.File(
        URI=f2URI,
        basepath=tempdir,
        group=DIFFERENT_GROUP_NAME)
rid = dp.put(
        vfsFile=f2,
        overwrite=False,
        LUID=None)
ok("Put different group file in nested dir", rid.get_UID() == Vfs.uri_join(dpdir,DIFFERENT_GROUP_NAME,NESTED_DIR_NAME,f2Name))

finished()
