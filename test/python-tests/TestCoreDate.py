#common sets up the conduit environment
from common import *

import os
import conduit
import conduit.datatypes.File as File
import conduit.utils as Utils

#check construction arg type checking
try:
    i = Utils.datetime_from_timestamp("Foo")
    ok("datetime_from_timestamp only accepts numbers", False)
except:
    ok("datetime_from_timestamp only accepts numbers", True)


try:
    i = Utils.datetime_from_timestamp("Foo")
    ok("datetime_get_timestamp only accepts datetimes", False)
except:
    ok("datetime_get_timestamp only accepts datetimes", True)

#make another local file
local = Utils.new_tempfile(Utils.random_string())

#get timestamp and mtimes
dt = local.get_mtime()
ts = Utils.datetime_get_timestamp(dt)

#now get timestamp using os.stat
pts = os.stat(local.get_local_uri()).st_mtime
pdt = Utils.datetime_from_timestamp(pts)

ok("Timestamps are equal (%s)" % ts, ts == pts)
ok("Datetimes are equal (%s)" % dt, dt == pdt)

#Check that we ignore any microsecond timestamps
f = ts + 0.01234
fdt = Utils.datetime_from_timestamp(f)
fts = Utils.datetime_get_timestamp(fdt)
ok("Ignore fractional timestamps (%s -> %s -> %s)" % (f,fts,dt), dt == fdt and ts == fts)

finished()

