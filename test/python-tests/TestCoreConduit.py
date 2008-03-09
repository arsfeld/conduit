#common sets up the conduit environment
from common import *

import conduit.Conduit as Conduit
test = SimpleTest()
cond = Conduit.Conduit(test.sync_manager)

ok("Conduit init OK", cond.is_empty() == True)
ok("Conduit Not busy", cond.is_busy() == False)

#add some dataproviders in different places
dps = test.get_dataprovider("TestSource")
dpk1 = test.get_dataprovider("TestSink")
dpk2 = test.get_dataprovider("TestFailRefresh")
dptw1 = test.get_dataprovider("TestTwoWay")
dptw2 = test.get_dataprovider("TestTwoWay") 
dptw3 = test.get_dataprovider("TestTwoWay") 

res = cond.add_dataprovider(dps)
ok("Add source", res == True)
res = cond.add_dataprovider(dps)
ok("One source only", res == False)
ok("Find source", dps in cond.get_all_dataproviders())
ok("Find source by key", dps in cond.get_dataproviders_by_key(dps.get_key()))
res = cond.delete_dataprovider(dps)
ok("Delete source", res == True)

res = cond.add_dataprovider(dpk1)
ok("Add sink", res == True)
res = cond.add_dataprovider(dpk1)
ok("Duplicate sink rejected", res == False)
res = cond.delete_dataprovider(dpk1)
ok("Delete sink", res == True)
res = cond.delete_dataprovider(dpk1)
ok("Delete non existing sink", res == False)

ok("Conduit empty", cond.is_empty() == True)

#add twoways into source and sink position
res = cond.add_dataprovider(dptw1, trySourceFirst=True)
ok("Add twoway as source", res == True and cond.get_dataprovider_position(dptw1) == (0,0))
res = cond.add_dataprovider(dptw2, trySourceFirst=True)
ok("Second twoway as sink", res == True and cond.get_dataprovider_position(dptw2) == (1,0))
res = cond.add_dataprovider(dptw3, trySourceFirst=False)
ok("Third twoway as sink", res == True and cond.get_dataprovider_position(dptw3) == (1,1))

#enable twoway
res = cond.can_do_two_way_sync()
ok("Twoway impossible", res == False)
res = cond.delete_dataprovider(dptw3)
ok("Delete sink", res == True)
res = cond.can_do_two_way_sync()
ok("Twoway possible", res == True)
res = cond.is_two_way()
ok("Twoway disabled by default", res == False)
cond.disable_two_way_sync()
cond.enable_two_way_sync()
res = cond.is_two_way()
ok("Twoway enabled", res == True)

#enable slow sync
cond.disable_slow_sync()
cond.enable_slow_sync()
res = cond.do_slow_sync()
ok("Slow sync enabled", res == True)

#refresh dp
cond.refresh_dataprovider(dptw1, block=True)
ok("Refresh dp", test.sync_manager.did_sync_abort(cond) == False and test.sync_manager.did_sync_error(cond) == False)
cond.refresh(block=True)
ok("Refresh", test.sync_manager.did_sync_abort(cond) == False and test.sync_manager.did_sync_error(cond) == False)
cond.sync(block=True)
ok("Sync", test.sync_manager.did_sync_abort(cond) == False and test.sync_manager.did_sync_error(cond) == False)

#swap some dps
cond.change_dataprovider(oldDpw=dptw1, newDpw=dps)
cond.change_dataprovider(oldDpw=dptw2, newDpw=dpk2)
ok("Swapped source", dps in cond.get_all_dataproviders())
ok("Swapped sink", dpk2 in cond.get_all_dataproviders())
res = cond.can_do_two_way_sync()
ok("Twoway no longer possible", res == False)

#refresh dp (should fail)
cond.refresh_dataprovider(dpk2, block=True)
ok("Refresh dp failed", test.sync_manager.did_sync_abort(cond) == True and test.sync_manager.did_sync_error(cond) == False)

finished()
