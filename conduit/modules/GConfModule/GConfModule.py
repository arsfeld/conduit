import gconf

import conduit
from conduit import log,logd,logw
import conduit.dataproviders.DataProvider as DataProvider

MODULES = {
    "GConfTwoWay"     : { "type": "dataprovider"  },
}

class GConfSetting(object):
    def __init__(self, key, value=""):
        self.key = key
        self.value = value

    def get_UID(self):
        return self.key

class GConfTwoWay(DataProvider.TwoWay):
    _name_ = "GConf Settings"
    _description_ = "Sync your desktop preferences"
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "setting"
    _out_type_ = "setting"
    _icon_ = "preferences-desktop"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.gconf = gconf.client_get_default()
        self.gconf.add_dir('/', gconf.CLIENT_PRELOAD_NONE)
        self.gconf.notify_add('/', self.on_change)

    def refresh(self):
        pass

    def _get_all(self, path):
        entries = []
        for x in self.gconf.all_dirs(path):
            entries += self._get_all(x)
        for x in self.gconf.all_entries(path):
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
            logw("can't sync, no schema for key: " + key)
            return

        # for some reason schema.get_type() appears to not exist
        dvalue = schema.get_default_value()
        if not dvalue:
            logw("no default value for " + key + " and right now we need one to get the key type")
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

    def get_all(self):
        """ loop through all gconf keys and see which ones match our whitelist """
        return self._get_all("/")

    def get(self, uid):
        """ Get a Setting object based on UID (key path) """
        node = self.gconf.get(uid)
        if not node:
            logd("Could not find uid %s" % uid)
            return None
        return GConfSetting(uid, self._from_gconf(node))

    def put(self, setting, overwrite, uid=None):
        logd("%s: %s" % (setting.key, setting.value))
        self._to_gonf(setting.key, setting.value)
        return setting.key

    def delete(self, uid):
        self.gconf.unset(uid)

    def on_change(self, client, id, entry, data):
        print "CHG:", dir(entry), data
        
    def get_UID(self):
        return self.__class__.__name__
