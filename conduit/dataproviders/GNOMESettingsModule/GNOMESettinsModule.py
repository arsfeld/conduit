import os
import gtk
import gconf
import gobject
import ConfigParser

import logging
import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
from conduit.datatypes import DataType
import conduit.datatypes.Text as Text

Utils.dataprovider_add_dir_to_path(__file__)
from GConfUtils import GConfImport, GConfExport

MODULES = {
	"GNOMESettings"     : { "type": "dataprovider"  },
    "SettingConverter"  : { "type": "converter"     }
}

#The directory the backup .cfg files reside in
CONFIG_DIR = "backups"
#ENUM of model indexes
ENABLED_IDX = 0
FILENAME_IDX = 1
NAME_IDX = 2
BACKUP_IDX = 3

class GNOMESettings(DataProvider.DataSource):

    _name_ = "GNOME Settings"
    _description_ = "Sync your desktop preferences"
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "gnome-setting"
    _out_type_ = "gnome-setting"
    _icon_ = "preferences-desktop"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)

        self.model = gtk.ListStore( gobject.TYPE_BOOLEAN,   #Enabled
                                    gobject.TYPE_STRING,    #Filename
                                    gobject.TYPE_STRING,    #Name
                                    gobject.TYPE_PYOBJECT   #Backup dict
                                    )

        #get all the backup config files
        confdir = os.path.join(os.path.dirname(__file__), CONFIG_DIR)
        if os.path.exists (confdir):
            for f in [os.path.join(confdir,i) for i in os.listdir(confdir)]:
                if os.path.isfile(f) and self._is_backup_config_file(f):
                    try:
                        filename,name,backup = self._parse_backup_config_file(f)
                        self.model.append((True,filename,name,backup))
                    except:
                        pass

    def _is_backup_config_file(self, filename):
        endswith = ".cfg"
        return filename[-len(endswith):] == endswith

    def _parse_backup_config_file(self, filename):
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

    def _build_view(self, view):
        #column0 is a checkbox with the number of enabled backups
        renderer = gtk.CellRendererToggle()
        renderer.set_property('activatable', True)
        renderer.connect( 'toggled', self._backup_enabled_toggled_cb)
        column0 = gtk.TreeViewColumn("Enabled", renderer, active=ENABLED_IDX)

        #column1 is the name of the backup
        column1 = gtk.TreeViewColumn("Name", gtk.CellRendererText(), text=NAME_IDX)
        column1.set_property("expand", True)
        column1.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)

        view.append_column(column0)
        view.append_column(column1)

    def _backup_enabled_toggled_cb(self, cell, path):
        self.model[path][ENABLED_IDX] = not self.model[path][ENABLED_IDX]
        return

    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        #little bit of hackery because index is actually the index
        #of enabled items in the model
        enabled = 0
        for i in self.model:
            if i[ENABLED_IDX]:
                if enabled == index:
                    return Setting(i[NAME_IDX],i[BACKUP_IDX])
                enabled += 1
            
    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        num = 0
        for i in self.model:
            if i[ENABLED_IDX] == True:
                num += 1
        return num
    
    def finish(self):
        pass

    def configure(self, window):
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"SettingsConfigDialog"
						)
        
        dlg = tree.get_widget("SettingsConfigDialog")
        view = tree.get_widget("settingstreeview")
        self._build_view(view)
        view.set_model(self.model)

        dlg.set_transient_for(window)
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            pass
        dlg.destroy()    


    def get_UID(self):
        return ""


class Setting(DataType.DataType):
    def __init__(self, name, backup):
        DataType.DataType.__init__(self,"gnome-setting")

        self.name = name
        self.GConfKeys = []
        self.GConfDirs = []

        if backup.has_key("GConfKey"):
            self.GConfKeys = backup["GConfKey"].split(";")

        if backup.has_key("GConfDir"):
            self.GConfDirs = backup["GConfDir"].split(";")

    def __str__(self):
        return "Settings for %s" % self.name

class SettingConverter:
    def __init__(self):
        self.conversions =  {    
                            "gnome-setting,text"    : self.to_text,
                            "gnome-setting,file"    : self.to_file
                            }
                            
    def _get_gconf_data_as_text (self, settings):
        client = gconf.client_get_default()
        gconfExporter = GConfExport(client)

        return gconfExporter.export(
                            settings.GConfDirs,
                            settings.GConfKeys
                            )

                            
    def to_text(self, setting):
        gconfText = self._get_gconf_data_as_text(setting)
        
        return Text.Text(
                        None,               #URI
                        text=str(setting)   #Raw contents
                        )

    def to_file(self, setting):
        gconfText = self._get_gconf_data_as_text(setting)
        return Utils.new_tempfile(gconfText)

