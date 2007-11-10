import gconf
import fnmatch
import logging
log = logging.getLogger("modules.GConf")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.AutoSync as AutoSync
from conduit.datatypes import DataType, Rid
import conduit.datatypes.Text as Text

MODULES = {
    "GConfTwoWay"     : { "type": "dataprovider"  },
    "GConfConverter"  : { "type": "converter" },
}

class GConfSetting(DataType.DataType):
    _name_ = "gconf-setting"

    def __init__(self, key, value=""):
        DataType.DataType.__init__(self)
        self.key = key
        self.value = value

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data["key"] = self.key
        data["value"] = self.value
        return data

    def __setstate__(self, data):
        self.key = data["key"]
        self.value = data["value"]
        DataType.DataType.__setstate__(self, data)

    def get_UID(self):
        return self.key


class GConfConverter(object):
    def __init__(self):
        self.conversions =  {    
                            "gconf-setting,text"    : self.to_text,
                            }
                            
    def to_text(self, setting):
        val = "%s, %s" % (setting.key, setting.value)
        return Text.Text(None, text=val)

class GConfTwoWay(DataProvider.TwoWay, AutoSync.AutoSync):
    _name_ = "GConf Settings"
    _description_ = "Sync your desktop preferences"
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "gconf-setting"
    _out_type_ = "gconf-setting"
    _icon_ = "preferences-desktop"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        AutoSync.AutoSync.__init__(self)

        self.whitelist = [
            '/apps/metacity/*',
            '/desktop/gnome/applications/*',
            '/desktop/gnome/background/*',
            '/desktop/gnome/interface/*',
            '/desktop/gnome/url-handlers/*'
        ]

        self.gconf = gconf.client_get_default()
        self.gconf.add_dir('/', gconf.CLIENT_PRELOAD_NONE)
        self.gconf.notify_add('/', self.on_change)

    def _onthelist(self, key):
        for pattern in self.whitelist:
            if fnmatch.fnmatch(key, pattern):
                return True
        return False

    def _get_all(self, path):
        entries = []
        for x in self.gconf.all_dirs(path):
            entries += self._get_all(x)
        for x in self.gconf.all_entries(path):
            if self._onthelist(x.key):
                entries.append(x.key)
        return entries

    def _gconf_type(self, key):
        node = self.gconf.get(key)
        if node:
            return node.type

        # Pinched from HP...
        # this is wrong, but schema.get_type() isn't in older gnome-python, only in svn head
        schema_key = "/schemas" + key 
        schema = gconf_client.get_schema(schema_key)
        if not schema:
            log.warn("can't sync, no schema for key: " + key)
            return

        # for some reason schema.get_type() appears to not exist
        dvalue = schema.get_default_value()
        if not dvalue:
            log.warn("no default value for " + key + " and right now we need one to get the key type")
            return
    
        return dvalue.type

    def _from_gconf(self, node):
        t = node.type
        val = ""
        if t == gconf.VALUE_INT:
            val = node.get_int()
        elif t == gconf.VALUE_STRING:
            val = node.get_string()
        elif t == gconf.VALUE_BOOL:
            val = node.get_bool()
        elif t == gconf.VALUE_FLOAT:
            val = node.get_float()
        elif t == gconf.VALUE_LIST:
            val = [self._from_gconf(x) for x in node.get_list()]
        return val

    def _to_gconf(self, key, value):
        t = self._gconf_type(key)
        if t == gconf.VALUE_INT:
            self.gconf.set_int(key, value)
        elif t == gconf.VALUE_STRING:
            self.gconf.set_string(key, value)
        elif t == gconf.VALUE_BOOL:
            self.gconf.set_bool(key, value)
        elif t == gconf.VALUE_FLOAT:
            self.gconf.set_float(key, value)
        elif t == gconf.VALUE_LIST:
            pass # val = [self._from_gconf(x) for x in item.get_list()]

    def refresh(self):
        pass

    def get_all(self):
        """ loop through all gconf keys and see which ones match our whitelist """
        return self._get_all("/")

    def get(self, uid):
        """ Get a Setting object based on UID (key path) """
        node = self.gconf.get(uid)
        if not node:
            log.debug("Could not find uid %s" % uid)
            return None
        return GConfSetting(uid, self._from_gconf(node))

    def put(self, setting, overwrite, uid=None):
        log.debug("%s: %s" % (setting.key, setting.value))
        self._to_gconf(setting.key, setting.value)
        #FIXME: Use an MD5...
        return Rid(uid=setting.key, hash=setting.value)

    def delete(self, uid):
        self.gconf.unset(uid)

    def on_change(self, client, id, entry, data):
        if self._onthelist(entry.key):
            self.handle_modified(entry.key)
        
    def get_UID(self):
        return self.__class__.__name__
