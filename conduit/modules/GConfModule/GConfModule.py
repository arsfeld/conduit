import fnmatch
import logging
log = logging.getLogger("modules.GConf")
from gettext import gettext as _

try:
    import gconf
except ImportError: # for maemo
    from gnome import gconf

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.AutoSync as AutoSync
import conduit.datatypes.Setting as Setting

MODULES = {
    "GConfTwoWay"     : { "type": "dataprovider"  }
}

class GConfTwoWay(DataProvider.TwoWay, AutoSync.AutoSync):
    _name_ = _("GConf Settings")
    _description_ = _("Sync your desktop preferences")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "setting"
    _out_type_ = "setting"
    _icon_ = "preferences-desktop"
    
    DEFAULT_WHITELIST = [
            '/apps/metacity/*',
            '/desktop/gnome/applications/*',
            '/desktop/gnome/background/*',
            '/desktop/gnome/interface/*',
            '/desktop/gnome/url-handlers/*'
        ]

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        AutoSync.AutoSync.__init__(self)

        self.whitelist = self.DEFAULT_WHITELIST

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
        return str(val)

    def _to_gconf(self, key, value):
        t = self._gconf_type(key)
        if t == gconf.VALUE_INT:
            self.gconf.set_int(key, int(value))
        elif t == gconf.VALUE_STRING:
            self.gconf.set_string(key, str(value))
        elif t == gconf.VALUE_BOOL:
            self.gconf.set_bool(key, bool(value))
        elif t == gconf.VALUE_FLOAT:
            self.gconf.set_float(key, float(value))
        elif t == gconf.VALUE_LIST:
            value = [self._from_gconf(x) for x in value]
            self.gconf.set_list(key, eval(value))

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
            
        s = Setting.Setting(
                        key=uid,
                        value=self._from_gconf(node)
                        )
        s.set_UID(uid)
        return s
        
    def get_configuration(self):
        return {"whitelist" : self.whitelist}
        
    def set_configuration(self, config):
        self.whitelist = config.get("whitelist",self.DEFAULT_WHITELIST)
        log.debug("%s" % self.whitelist)

    def put(self, setting, overwrite, uid=None):
        log.debug("%s: %s" % (setting.key, setting.value))
        self._to_gconf(setting.key, setting.value)
        return setting.get_rid()

    def delete(self, uid):
        self.gconf.unset(uid)

    def on_change(self, client, id, entry, data):
        if self._onthelist(entry.key):
            self.handle_modified(entry.key)
        
    def get_UID(self):
        return self.__class__.__name__
