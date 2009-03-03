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
    _name_ = _("Application Settings")
    _description_ = _("Synchronize your application settings")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "twoway"
    _in_type_ = "setting"
    _out_type_ = "setting"
    _icon_ = "preferences-desktop"
    _configurable_ = True
    
    WHITELIST = (
        ("Metacity",                "/apps/metacity/*"),
        ("Nautilus",                "/apps/nautilus/*"),
        ("Preferred Applications",  "/desktop/gnome/applications/*"),
        ("Desktop Interface",       "/desktop/gnome/interface/*"),
        ("Gnome Terminal",          "/apps/gnome-terminal/*")
    )

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        AutoSync.AutoSync.__init__(self)
        self.update_configuration(
            sections = []
        )
        self.awaitingChanges = {}
        self.gconf = gconf.client_get_default()
        self.gconf.add_dir('/', gconf.CLIENT_PRELOAD_NONE)
        self.gconf.notify_add('/', self._on_change)

    def _in_the_list(self, key):
        for pattern in self.sections:
            if fnmatch.fnmatch(key, pattern):
                return True
        return False

    def _get_all(self, path):
        entries = []
        for x in self.gconf.all_dirs(path):
            entries += self._get_all(x)
        for x in self.gconf.all_entries(path):
            if self._in_the_list(x.key):
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
            val = int(value)
            func = self.gconf.set_int
        elif t == gconf.VALUE_STRING:
            val = str(value)
            func = self.gconf.set_string
        elif t == gconf.VALUE_BOOL:
            val = bool(value)
            func = self.gconf.set_bool
        elif t == gconf.VALUE_FLOAT:
            val = float(value)
            func = self.gconf.set_float
        elif t == gconf.VALUE_LIST:
            val = eval([self._from_gconf(x) for x in value])
            func = self.gconf.set_list
        else:
            log.warn("Unknown gconf key: %s" % key)
            return

        #We will get a notification that a key has changed.
        #ignore it (because we made the change)
        self.awaitingChanges[key] = val
        #bit of a dance to ensure that we edit awaitingChanges before we
        #make the change
        func(key, val)

    def _on_change(self, client, id, entry, data):
        if self._in_the_list(entry.key):
            #check to see if the change was one of ours
            try:
                del(self.awaitingChanges[entry.key])
            except KeyError:
                #the change wasnt from us
                self.handle_modified(entry.key)

    def config_setup(self, config):
        config.add_section(_("Applications to Synchronize"))
        items_config = config.add_item("Items", "list",
            config_name = "sections",
            choices = [(path, name) for name, path in self.WHITELIST]
        )

    def get_all(self):
        """ loop through all gconf keys and see which ones match our whitelist """
        DataProvider.TwoWay.get_all(self)
        if self.sections:
            return self._get_all("/")
        else:
            return []

    def get(self, uid):
        """ Get a Setting object based on UID (key path) """
        DataProvider.TwoWay.get(self, uid)
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
        
    def put(self, setting, overwrite, uid=None):
        DataProvider.TwoWay.put(self, setting, overwrite, uid)
        log.debug("Saving value in Gconf: %s=%s" % (setting.key, setting.value))
        self._to_gconf(setting.key, setting.value)
        if uid == None:
            uid = setting.key
        return self.get(uid).get_rid()

    def delete(self, uid):
        DataProvider.TwoWay.delete(self, uid)
        self.gconf.unset(uid)

    def get_UID(self):
        return self.__class__.__name__
