import os.path
from gettext import gettext as _
import logging
log = logging.getLogger("modules.File")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.File as FileDataProvider
import conduit.dataproviders.AutoSync as AutoSync
import conduit.Utils as Utils
import conduit.Vfs as Vfs

MODULES = {
	"FileSource" :      { "type": "dataprovider" },
	"FolderTwoWay" :    { "type": "dataprovider" },
#    "USBFactory" :      { "type": "dataprovider-factory" }
}

TYPE_FILE = "0"
TYPE_FOLDER = "1"

class FileSource(FileDataProvider.FileSource):

    _name_ = _("Files")
    _description_ = _("Source for synchronizing multiple files")

    def __init__(self, *args):
        FileDataProvider.FileSource.__init__(self)

    def configure(self, window):
        Utils.dataprovider_add_dir_to_path(__file__, "")
        import FileConfiguration
        f = FileConfiguration._FileSourceConfigurator(window, self.db)
        response = f.show_dialog()
       
    def set_configuration(self, config):
        for f in config.get("files",[]):
            self._add_file(f)
        for f in config.get("folders",[]):
            f,group = f.split("---FIXME---")
            if Utils.get_protocol(f) != "":
                self._add_folder(f,group)
        self.db.debug(200,True)

    def get_configuration(self):
        files = []
        folders = []
        for uri,ftype,group in self.db.select("SELECT URI,TYPE,GROUP_NAME FROM config"):
            if ftype == TYPE_FILE:
                files.append(uri)
            else:
                folders.append("%s---FIXME---%s" % (uri,group))

        self.db.save()

        return {"files" : files,
                "folders" : folders}

    def get_UID(self):
        return Utils.get_user_string()

class FolderTwoWay(FileDataProvider.FolderTwoWay, AutoSync.AutoSync):
    """
    TwoWay dataprovider for synchronizing a folder
    """

    _name_ = _("Folder")
    _description_ = _("Synchronize folders")

    DEFAULT_FOLDER = os.path.expanduser("~")
    DEFAULT_GROUP = "Home"
    DEFAULT_HIDDEN = False
    DEFAULT_COMPARE_IGNORE_MTIME = False

    def __init__(self, *args):
        FileDataProvider.FolderTwoWay.__init__(self,
                FolderTwoWay.DEFAULT_FOLDER,
                FolderTwoWay.DEFAULT_GROUP,
                FolderTwoWay.DEFAULT_HIDDEN,
                FolderTwoWay.DEFAULT_COMPARE_IGNORE_MTIME
                )
        AutoSync.AutoSync.__init__(self)
        self.need_configuration(True)

        self._monitor_folder_id = None

    def __del__(self):
        if self._monitor_folder_id != None:
            Vfs.monitor_cancel(self._monitor_folder_id)
            self._monitor_folder_id = None

    def configure(self, window):
        Utils.dataprovider_add_dir_to_path(__file__, "")
        import FileConfiguration
        f = FileConfiguration._FolderTwoWayConfigurator(window, self.folder, self.folderGroupName, self.includeHidden, self.compareIgnoreMtime)
        self.folder, self.folderGroupName, self.includeHidden, self.compareIgnoreMtime = f.show_dialog()
        self.set_configured(True)
        self._monitor_folder()
        
    def set_configuration(self, config):
        self.folder = config.get("folder", FolderTwoWay.DEFAULT_FOLDER)
        self.folderGroupName = config.get("folderGroupName", FolderTwoWay.DEFAULT_GROUP)
        self.includeHidden = config.get("includeHidden", FolderTwoWay.DEFAULT_HIDDEN)
        self.compareIgnoreMtime = config.get("compareIgnoreMtime", FolderTwoWay.DEFAULT_COMPARE_IGNORE_MTIME)

        self.set_configured(True)
        self._monitor_folder()

    def get_configuration(self):
        #_save_config_file_for_dir(self.folder, self.folderGroupName)
        return {
            "folder" : self.folder,
            "folderGroupName" : self.folderGroupName,
            "includeHidden" : self.includeHidden,
            "compareIgnoreMtime" : self.compareIgnoreMtime
            }

    def get_UID(self):
        return "%s:%s" % (self.folder, self.folderGroupName)

    def _monitor_folder(self):
        if self._monitor_folder_id != None:
            Vfs.monitor_cancel(self._monitor_folder_id)
            self._monitor_folder_id = None

        self._monitor_folder_id = Vfs.monitor_add(self.folder, Vfs.MONITOR_DIRECTORY, self._monitor_folder_cb)            

    def _monitor_folder_cb(self, monitor_uri, event_uri, event, data=None):
        """
        Called when a file in the current folder is changed, added or deleted
        """
        # supported events = CHANGED, DELETED, CREATED
        if event == Vfs.MONITOR_EVENT_CREATED:
            self.handle_added(event_uri)
        elif event == Vfs.MONITOR_EVENT_CHANGED:
            self.handle_modified(event_uri)
        elif event == Vfs.MONITOR_EVENT_DELETED:
            self.handle_deleted(event_uri)

class USBFactory(DataProvider.DataProviderFactory):
    def __init__(self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)

        if kwargs.has_key("hal"):
            self.hal = kwargs["hal"]
            self.hal.connect("usb-added", self._usb_added)
            self.hal.connect("usb-removed", self._usb_removed)

        self.usb = {}

    def probe(self):
        """
        Probe for USB Keys that are already attached
        """
        for device_type, udi, mount, name in self.hal.get_all_usb_keys():
            self._usb_added(None, udi, mount, name)

    def _usb_added(self, hal, udi, mount, name):
        """
        New USB key has been discovered
        """
        cat = DataProvider.DataProviderCategory(
                    name,
                    "drive-removable-media",
                    mount)

        keys = []
        for klass in [FileSource]:
            key = self.emit_added(
                           klass,            # Dataprovider class
                           (mount,udi,),     # Init args
                           cat)              # Category..
            keys.append(key)

        self.usb[udi] = keys

    def _usb_removed(self, hal, udi, mount, name):
        for key in self.usb[udi]:
            self.emit_removed(key)

        del self.usb[udi]

