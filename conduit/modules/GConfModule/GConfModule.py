import gconf

import conduit
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

    def get_all(self):
        """ loop through all gconf keys and see which ones match our whitelist """
        return self._get_all("/")

    def get(self, uid):
        """ Get a Setting object based on UID (key path) """
        value = self.gconf.get(uid)
        #if value == None:
        #    raise SomeError
        return GConfSetting(uid, value)

    def put(self, setting, overwrite, uid=None):
        logd("%s: %s" % (setting.key, setting.value))
        return setting.key

    def delete(self, uid):
        self.gconf.unset(uid)

    def on_change(self, client, id, entry, data):
        print "CHG:", dir(entry), data
        
    def get_UID(self):
        return self.__class__.__name__
