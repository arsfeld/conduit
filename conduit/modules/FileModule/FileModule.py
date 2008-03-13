import os.path
from gettext import gettext as _
import logging
log = logging.getLogger("modules.File")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.File as FileDataProvider
import conduit.dataproviders.VolumeFactory as VolumeFactory
import conduit.dataproviders.AutoSync as AutoSync
import conduit.Utils as Utils
import conduit.Vfs as Vfs

MODULES = {
	"FileSource" :              { "type": "dataprovider" },
	"FolderTwoWay" :            { "type": "dataprovider" },
#    "RemovableDeviceFactory" :  { "type": "dataprovider-factory" }
}

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
            self._add_folder(f,group)

    def get_configuration(self):
        files = []
        folders = []
        for uri,ftype,group in self.db.select("SELECT URI,TYPE,GROUP_NAME FROM config"):
            if ftype == FileDataProvider.TYPE_FILE:
                files.append(uri)
            else:
                folders.append("%s---FIXME---%s" % (uri,group))

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

    DEFAULT_FOLDER = "file://"+os.path.expanduser("~")
    DEFAULT_GROUP = "Home"
    DEFAULT_HIDDEN = False
    DEFAULT_COMPARE_IGNORE_MTIME = False

    def __init__(self, *args):
        print "#"*100,self.DEFAULT_FOLDER
        FileDataProvider.FolderTwoWay.__init__(self,
                self.DEFAULT_FOLDER,
                self.DEFAULT_GROUP,
                self.DEFAULT_HIDDEN,
                self.DEFAULT_COMPARE_IGNORE_MTIME
                )
        AutoSync.AutoSync.__init__(self)
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
        self._monitor_folder()
        
    def set_configuration(self, config):
        self.folder = config.get("folder", self.DEFAULT_FOLDER)
        self.folderGroupName = config.get("folderGroupName", self.DEFAULT_GROUP)
        self.includeHidden = config.get("includeHidden", self.DEFAULT_HIDDEN)
        self.compareIgnoreMtime = config.get("compareIgnoreMtime", self.DEFAULT_COMPARE_IGNORE_MTIME)
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
        
    def get_name(self):
        return self.folderGroupName

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

class RemovableDeviceFactory(VolumeFactory.VolumeFactory):

    def __init__(self, **kwargs):
        VolumeFactory.VolumeFactory.__init__(self, **kwargs)
        self.foo = {}

    def _make_class(self, folder, name):
        klass = type(
                "FolderTwoWay",
                (FolderTwoWay,),
                {"DEFAULT_FOLDER":folder,"DEFAULT_GROUP":name}
                )
        return klass

    def emit_added(self, klass, initargs, category):
        """
        Override emit_added to allow duplictes.
        """
        VolumeFactory.VolumeFactory.emit_added(self, klass, initargs, category, customKey="12345")

    def is_interesting(self, udi, props):
        if props.has_key("info.parent") and props.has_key("info.parent") != "":
            prop2 = self._get_properties(props["info.parent"])
            if prop2.has_key("storage.removable") and prop2["storage.removable"] == True:
                mount,label = self._get_device_info(props)
                #check for the presence of a mount/.conduit file
                #which describe the folder sync groups, and their names, 
                #on this volume
                #
                #The format of this file is n lines in the form
                # group_name|path
                # group_name|path
                path = Vfs.uri_join(mount,".conduit")
                if Vfs.uri_exists(path):
                    self.foo[udi] = [self._make_class("/tmp",i) for i in range(2)]
                return True
        return False
    
    def get_category(self, udi, **kwargs):
        return DataProviderCategory.DataProviderCategory(
                    kwargs['label'],
                    "multimedia-player-ipod-video-white",
                    udi)

    def get_dataproviders(self, udi, **kwargs):
         return self.foo[udi]
         
    def get_args(self, udi, **kwargs):
        return ()

