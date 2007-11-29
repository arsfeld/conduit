import os
import gobject
import tarfile
import tempfile
import ConfigParser
import logging
log = logging.getLogger("modules.Settings")

import conduit
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
from conduit.datatypes import DataType
import conduit.datatypes.Text as Text
import conduit.datatypes.File as File

Utils.dataprovider_add_dir_to_path(__file__)
from GConfUtils import GConfImport, GConfExport

from gettext import gettext as _

MODULES = {
#	"Settings"     : { "type": "dataprovider"  },
#    "SettingConverter"  : { "type": "converter"     }
}

#The directory the backup .cfg files reside in
CONFIG_DIR = "settings"
#ENUM of model indexes
ENABLED_IDX = 0
FILENAME_IDX = 1
NAME_IDX = 2
BACKUP_IDX = 3

class Settings(DataProvider.DataSource):

    _name_ = _("System Settings")
    _description_ = _("Sync your desktop preferences")
    _category_ = conduit.dataproviders.CATEGORY_MISC
    _module_type_ = "source"
    _in_type_ = "setting"
    _out_type_ = "setting"
    _icon_ = "preferences-desktop"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        import gtk
        self.model = gtk.ListStore( gobject.TYPE_BOOLEAN,   #Enabled
                                    gobject.TYPE_STRING,    #Filename
                                    gobject.TYPE_STRING,    #Name
                                    gobject.TYPE_PYOBJECT   #Backup dict
                                    )

        #get all the backup config files
        confdir = os.path.join(os.path.dirname(__file__), CONFIG_DIR)
        if os.path.exists (confdir):
            for f in [os.path.join(confdir,i) for i in os.listdir(confdir)]:
                if os.path.isfile(f) and self._is_settings_config_file(f):
                    try:
                        filename,name,backup = self._parse_settings_config_file(f)
                        self.model.append((True,filename,name,backup))
                    except:
                        pass

    def _is_settings_config_file(self, filename):
        endswith = ".cfg"
        return filename[-len(endswith):] == endswith

    def _parse_settings_config_file(self, filename):
        parser = ConfigParser.RawConfigParser()
        parser.read([filename])
        if not parser.has_section("Backup"):
            log.warn("Cannot parse backup config file %s" % filename)
            raise Exception

        #get the translated display name
        name = os.path.basename(filename)
        if parser.has_section("Display") and parser.has_option("Display", "Name"):
            name = parser.get("Display", "Name")

        backups={}
        for opt in ["GConfKey", "GConfDir", "File", "Directory"]:
            if parser.has_option("Backup", opt):
                backups[opt] = parser.get("Backup", opt)

        return filename,name,backups

    def _build_view(self, view):
        import gtk
        #column0 is a checkbox with the number of enabled backups
        renderer = gtk.CellRendererToggle()
        renderer.set_property('activatable', True)
        renderer.connect( 'toggled', self._backup_enabled_toggled_cb)
        column0 = gtk.TreeViewColumn(_("Enabled"), renderer, active=ENABLED_IDX)

        #column1 is the name of the backup
        column1 = gtk.TreeViewColumn(_("Name"), gtk.CellRendererText(), text=NAME_IDX)
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
        
#     def get(self, index):
#         DataProvider.DataSource.get(self, index)
#         #little bit of hackery because index is actually the index
#         #of enabled items in the model
#         enabled = 0
#         for i in self.model:
#             if i[ENABLED_IDX]:
#                 if enabled == index:
#                     return Setting(i[NAME_IDX],i[BACKUP_IDX])
#                 enabled += 1
#             
#     def get_all(self):
#         DataProvider.DataSource.get_all(self)
#         num = 0
#         for i in self.model:
#             if i[ENABLED_IDX] == True:
#                 num += 1
#         return num
    
    def finish(self):
        DataProvider.DataSource.finish(self)

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

        response = Utils.run_dialog (dlg, window)
        if response == True:
            pass
        dlg.destroy()    


    def get_UID(self):
        return ""


class Setting(DataType.DataType):
    _name_ = "setting"
    def __init__(self, name, backup):
        DataType.DataType.__init__(self)

        self.name = name
        self.GConfKeys = []
        self.GConfDirs = []
        self.Files = []
        self.Directories = []

        if backup.has_key("GConfKey"):
            self.GConfKeys = backup["GConfKey"].split(";")

        if backup.has_key("GConfDir"):
            self.GConfDirs = backup["GConfDir"].split(";")

        if backup.has_key("File"):
            self.Files = [os.path.expanduser(i) for i in backup["File"].split(";")]

        if backup.has_key("Directory"):
            self.Directories = [os.path.expanduser(i) for i in backup["Directory"].split(";")]

    def __str__(self):
        return "Settings for %s" % self.name

class SettingConverter:
    def __init__(self):
        self.conversions =  {    
                            "setting,text"    : self.to_text,
                            "setting,file"    : self.to_file
                            }
                            
    def _get_gconf_data_as_text (self, settings):
        text = None
        if len(settings.GConfDirs + settings.GConfKeys) > 0:
            gconfExporter = GConfExport()
            text = gconfExporter.export(
                            settings.GConfDirs,
                            settings.GConfKeys
                            )

        return text

                            
    def to_text(self, setting):
        gconfText = self._get_gconf_data_as_text(setting)
        if gconfText == None:
            raise Exception("Settings %s has no settings to convert" % setting.name)
        
        return Text.Text(
                        None,               #URI
                        text=str(setting)   #Raw contents
                        )

    def to_file(self, setting):
        tmpDir = tempfile.mkdtemp()

        #create the tar file
        uniqueName = "%s-%s-Settings-%s.tar.gz" % (
                                        conduit.APPNAME, 
                                        conduit.APPVERSION, 
                                        setting.name
                                        )
        tarFileName = os.path.join(tmpDir, uniqueName)
        tarFile = tarfile.open(tarFileName,'w:gz')

        #the gconf info is always stored in the archive as gconf.xml
        gconfText = self._get_gconf_data_as_text(setting)
        if gconfText != None:
            gconfFileName = os.path.join(tmpDir, "gconf.xml")
            f = open(gconfFileName, 'w') 
            f.write(gconfText)
            f.close()
            tarFile.add(gconfFileName, os.path.basename(gconfFileName))

        #add all files/folders. if they are in the users home dir then add
        #the relative path. If they are in / then add full path
        for i in setting.Files + setting.Directories:
            home = os.path.expanduser("~")
            if i.find(home) == -1:
                tarFile.add(i)
            else:
                tarFile.add(i, i.replace(home,""))
                
        tarFile.close()
            
        return File.File(tarFileName)

