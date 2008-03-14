#common sets up the conduit environment
from common import *

import conduit.dataproviders.File as FileDataProvider
import conduit.Vfs as Vfs

#Test removable volume support
removableUri = get_external_resources('folder')['removable-volume']
ok("Is on a removable volume", FileDataProvider.is_on_removable_volume(removableUri))

#save and restore a group
groupName = "GroupName Is Lame"
groupInfo = (removableUri, groupName)
ok("Save group info", FileDataProvider.save_removable_volume_group_file(*groupInfo))
readInfo = FileDataProvider.read_removable_volume_group_file(removableUri)
ok("Read group info (%s)" % str(readInfo), len(readInfo) > 0 and readInfo[0][1] == groupName)
finished()
