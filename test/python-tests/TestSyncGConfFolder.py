#common sets up the conduit environment
from common import *

#setup test
test = SimpleSyncTest()

#Setup the key to sync
gconf = test.get_dataprovider("GConfTwoWay")
gconf.module.whitelist = ['/apps/metacity/general/num_workspaces']
folder = test.get_dataprovider("TestFolderTwoWay")

test.prepare(gconf, folder)
test.set_two_way_policy({"conflict":"ask","deleted":"ask"})
test.set_two_way_sync(True)

a = test.get_source_count()
b = test.get_sink_count()
ok("Got items to sync (%s,%s)" % (a,b), a == 1 and b == 0)

for i in (1,2,3,4):
    if i > 1:
        #Now modify the file
        f = folder.module.get(
                folder.module.get_all()[0]
                )
        f._set_file_mtime(datetime.datetime(2008,1,i))

    a,b = test.sync()
    aborted,errored,conflicted = test.get_sync_result()
    ok("Sync #%s: Completed without conflicts" % i, aborted == False and errored == False and conflicted == False)
    ok("Sync #%s: All items (%s,%s)" % (i,a,b), a == b and a == 1)

finished()

