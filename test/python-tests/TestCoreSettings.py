#common sets up the conduit environment
from common import *

import conduit.Settings as Settings

import os

#Value not important. Needed to compare TYPES
SETTINGS = {
        'gui_expanded_rows'         :   [],
        'gui_hpane_postion'         :   250,
        'gui_minimize_to_tray'      :   False,
        'default_policy_conflict'   :   "ask"
}

if os.environ.has_key("CONDUIT_SETTINGS_IMPL"):
    impls = (os.environ["CONDUIT_SETTINGS_IMPL"],)
else:
    impls = ("GConf", "Python")
for impl in impls:
    ok("--- TESTING SETTINGS IMPL: %s" % impl, True)

    s = Settings.Settings(implName=impl)

    for k,v in SETTINGS.items():
        val = s.get(k)
        ok("Settings returned correct type (%s) for %s" % (type(val),k), type(val) == type(v))
        i = s.set(k,val)
        ok("Save setting %s OK" % k, i)

    #Override defaults
    val = s.get("foo",default="bar")
    ok("Defaults function params override defaults", type(val) == str and val == "bar")

    #test error paths
    i = s.set("foo",lambda x: x)
    ok("Unknown types not saved", i == False)

    i = s.get("foo")
    ok("Unknown keys not fetched", i == None)

    i = s.get("foo", default=lambda x: x)
    ok("Unknown keys with invalid defaults not fetched", i == None)

    #Test proxy
    os.environ['http_proxy'] = "http://foo:bar@132.181.1.1:8080"
    ok("Detect proxy", s.proxy_enabled())
    ok("Parse environment variables proxy", s.get_proxy() == ('132.181.1.1', 8080, 'foo', 'bar'))

    #Test overridden settings are not set
    s.set_overrides(cheese="swiss")
    orig = s.get('cheese')
    setOK = s.set('cheese', 'colby')
    new = s.get('cheese')
    ok("Overridden settings not saved", setOK == True and orig == new and new == "swiss")

finished()
