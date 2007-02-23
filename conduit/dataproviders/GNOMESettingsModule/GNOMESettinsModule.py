import os
import gtk
import gobject
import ConfigParser

import logging
import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider

Utils.dataprovider_add_dir_to_path(__file__)
from GConfUtils import GConfImport, GConfExport

MODULES = {
	"GNOMESettings" : { "type": "dataprovider" }
}

#The directory the backup .cfg files reside in
CONFIG_DIR = "backups"

class GNOMESettings(DataProvider.DataSource):

    _name_ = "GNOME Settings"
    _description_ = "Sync your desktop preferences"
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "gnome-settings"
    _out_type_ = "file"
    _icon_ = "preferences-desktop"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #get all the backup config files
        confdir = os.path.join(os.path.dirname(__file__), CONFIG_DIR)
        if os.path.exists (confdir):
            self.backupConfigFiles = [os.path.join(confdir,i) for i in os.listdir(confdir)]
        else:
            self.backupConfigFiles = []

        #list of settings names that should be synced. index is the filename of
        #a config file in self.backupConfigFiles
        self.enabled = []

    def _parse_config_file(self, filename):
        parser = ConfigParser.RawConfigParser()
        parser.read([filename])
        if not parser.has_section("Backup"):
            logw("Cannot parse backup config file %s" % filename)
            raise Exception

        #get the translated display name
        name = os.path.basename(filename)
        if parser.has_section("Display") and parser.has_option("Display", "Name"):
            name = parser.get("Display", "Name")

        backups={}
        for opt in ["GConfKey", "GConfDir"]:
            if parser.has_option("Backup", opt):
                backups[opt] = parser.get("Backup", opt)

        return filename,name,backups

    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return None

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return 0
    
    def finish(self):
        pass

    def configure(self, window):
        #tree = Utils.dataprovider_glade_get_widget(
        #                __file__, 
        #                "config.glade",
		#				"SettingsConfigDialog"
		#				)
        #
        #dlg = tree.get_widget("SettingsConfigDialog")
        #view = tree.get_widget("settingstreeview")
        for i in self.backupConfigFiles:
            print self._parse_config_file(i)

    def get_UID(self):
        return ""


