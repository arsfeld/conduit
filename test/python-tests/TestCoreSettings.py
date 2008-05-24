import os

#common sets up the conduit environment
from common import *

import conduit.Settings as Settings

s = Settings.Settings()

#Value not important. Needed to compare TYPES
SETTINGS = {
        'gui_expanded_rows'         :   [],
        'gui_hpane_postion'         :   250,
        'gui_minimize_to_tray'      :   False,
        'web_login_browser'         :   "system"
}

for k,v in SETTINGS.items():
    val = s.get(k)
    ok("Settings returned correct type (%s) for %s" % (type(val),k), type(val) == type(v))
    i = s.set(k,val)
    ok("Save setting %s OK" % k, i)

#Override defaults
val = s.get("foo",vtype=str,default="bar")
ok("Defaults function params override defaults", type(val) == str and val == "bar")

#test error paths
i = s.set("foo",lambda x: x)
ok("Unknown types not saved", i == False)

#test error paths
i = s.get("foo")
ok("Unknown keys not fetched", i == None)

#Test proxy
os.environ['http_proxy'] = "http://foo:bar@132.181.1.1:8080"
ok("Detect proxy", s.proxy_enabled())
ok("Parse environment variables proxy", s.get_proxy() == ('132.181.1.1', 8080, 'foo', 'bar'))

finished()
