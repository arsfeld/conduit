#common sets up the conduit environment
from common import *

import conduit.utils.Bluetooth as Bluetooth

#test the bluetooth searching singleton
def found_phone(address, name):
    pass

def found_pc(address, name):
    pass

a = Bluetooth.BluetoothSearcher()
b = Bluetooth.BluetoothSearcher()

ok("Bluetooth searcher is singleton", a != None and a == b)

a.watch_for_devices(found_phone)
b.watch_for_devices(found_phone)
ok("Registered found_phone function", len(a._cbs) == 1)

b.watch_for_devices(found_pc, class_check_func=Bluetooth.is_computer_class)
ok("Registered found_pc function", len(a._cbs) == 2)

wait_seconds(2)
ok("Bluetooth search thread started", a.isAlive())

try:
    a.cancel()
    a.join(a.SLEEP_TIME)
    ok("Cancelled scan (found %d devices)" % len(a.get_devices()), True)
except Exception:
    ok("Cancelled scan", False)

finished()
