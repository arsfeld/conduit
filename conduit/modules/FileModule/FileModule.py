import os.path
from gettext import gettext as _
import logging
log = logging.getLogger("modules.File")

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.DataProviderCategory as DataProviderCategory
import conduit.dataproviders.File as FileDataProvider
import conduit.dataproviders.SimpleFactory as SimpleFactory
import conduit.dataproviders.AutoSync as AutoSync
import conduit.utils as Utils
import conduit.Vfs as Vfs

MODULES = {
    "FileSource" :              { "type": "dataprovider" },
    "FolderTwoWay" :            { "type": "dataprovider" },
    "RemovableDeviceFactory" :  { "type": "dataprovider-factory" }
}

class FileSource(FileDataProvider.FileSource):

    _name_ = _("Files")
    _description_ = _("Source for synchronizing multiple files")
    _configurable_ = True

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
    _configurable_ = True

    DEFAULT_FOLDER = "file://"+os.path.expanduser("~")
    DEFAULT_GROUP = "Home"
    DEFAULT_HIDDEN = False
    DEFAULT_COMPARE_IGNORE_MTIME = False
    DEFAULT_FOLLOW_SYMLINKS = False

    def __init__(self, *args):
        FileDataProvider.FolderTwoWay.__init__(self,
                self.DEFAULT_FOLDER,
                self.DEFAULT_GROUP,
                self.DEFAULT_HIDDEN,
                self.DEFAULT_COMPARE_IGNORE_MTIME,
                self.DEFAULT_FOLLOW_SYMLINKS
                )
        AutoSync.AutoSync.__init__(self)
        self._monitor = Vfs.FileMonitor()
        self._monitor.connect("changed", self._monitor_folder_cb)

    def __del__(self):
        self._monitor.cancel()
            
    def configure(self, window):
        Utils.dataprovider_add_dir_to_path(__file__, "")
        import FileConfiguration
        f = FileConfiguration._FolderTwoWayConfigurator(
                                    window,
                                    self.folder,
                                    self.includeHidden,
                                    self.compareIgnoreMtime,
                                    self.followSymlinks)
        self.folder, self.includeHidden, self.compareIgnoreMtime, self.followSymlinks = f.show_dialog()
        self._monitor_folder()
        
    def set_configuration(self, config):
        self.folder = config.get("folder", self.DEFAULT_FOLDER)
        self.includeHidden = config.get("includeHidden", self.DEFAULT_HIDDEN)
        self.compareIgnoreMtime = config.get("compareIgnoreMtime", self.DEFAULT_COMPARE_IGNORE_MTIME)
        self.followSymlinks = config.get("followSymlinks", self.DEFAULT_FOLLOW_SYMLINKS)        
        self._monitor_folder()

    def get_configuration(self):
        return {
            "folder" : self.folder,
            "includeHidden" : self.includeHidden,
            "compareIgnoreMtime" : self.compareIgnoreMtime,
            "followSymlinks" : self.followSymlinks
            }

    def get_UID(self):
        return self.folder
        
    def get_name(self):
        return Vfs.uri_get_filename(self.folder)

    def _monitor_folder(self):
        self._monitor.add(self.folder, self._monitor.MONITOR_DIRECTORY)

    def _monitor_folder_cb(self, sender, event_uri, event):
        """
        Called when a file in the current folder is changed, added or deleted
        """
        # supported events = CHANGED, DELETED, CREATED
        if event == self._monitor.MONITOR_EVENT_CREATED:
            self.handle_added(event_uri)
        elif event == self._monitor.MONITOR_EVENT_CHANGED:
            self.handle_modified(event_uri)
        elif event == self._monitor.MONITOR_EVENT_DELETED:
            self.handle_deleted(event_uri)

class RemovableDeviceFactory(SimpleFactory.SimpleFactory):

    def __init__(self, **kwargs):
        SimpleFactory.SimpleFactory.__init__(self, **kwargs)
        self._volumes = {}
        self._categories = {}
        self._vm = Vfs.VolumeMonitor()
        self._vm.connect("volume-mounted",self._volume_mounted_cb)
        self._vm.connect("volume-unmounted",self._volume_unmounted_cb)

    def _volume_mounted_cb(self, monitor, device_udi, mount, label):
        log.info("Volume mounted, %s : (%s : %s)" % (device_udi,mount,label))
        if device_udi:
            self._check_preconfigured(device_udi, mount, label)
            self.item_added(device_udi, mount=mount, label=label)

    def _volume_unmounted_cb(self, monitor, device_udi):
        log.info("Volume unmounted, %s" % device_udi)
        if device_udi and device_udi in self._volumes:
            self.item_removed(device_udi)

    def _make_class(self, udi, folder, name):
        log.info("Creating preconfigured folder dataprovider: %s" % folder)
        info = {    
            "DEFAULT_FOLDER":   folder,
            "_udi_"         :   udi
        }
        if name:
            info["_name_"] = name            
        
        klass = type(
                "FolderTwoWay",
                (FolderTwoWay,),
                info)
        return klass

    def _check_preconfigured(self, udi, mountUri, label):
        #check for the presence of a mount/.conduit group file
        #which describe the folder sync groups, and their names,
        try:
            groups = FileDataProvider.read_removable_volume_group_file(mountUri)
        except Exception, e:
            log.warn("Error reading volume group file: %s" % e)
            groups = ()
            
        if len(groups) > 0:
            self._volumes[udi] = []
            for relativeUri,name in groups:
                klass = self._make_class(
                                    udi=udi,
                                    #uri is relative, make it absolute
                                    folder="%s%s" % (mountUri,relativeUri),
                                    name=name)
                self._volumes[udi].append(klass)
        else:
            klass = self._make_class(
                                udi=udi,
                                folder=mountUri,
                                name=None)
            self._volumes[udi] = [klass]

    def probe(self):
        """
        Called after initialised to detect already connected volumes
        """
        volumes = self._vm.get_mounted_volumes()
        for device_udi in volumes:
            if device_udi:
                mount,label = volumes[device_udi]
                self._check_preconfigured(device_udi, mount, label)
                self.item_added(device_udi, mount=mount, label=label)
            if device_udi:
                mount,label = volumes[device_udi]
                self.item_added(device_udi, mount=mount, label=label)

    def emit_added(self, klass, initargs, category):
        """
        Override emit_added to allow duplictes. The custom key is based on
        the folder and the udi to allow multiple preconfigured groups per
        usb key
        """
        return SimpleFactory.SimpleFactory.emit_added(self, 
                        klass, 
                        initargs, 
                        category, 
                        customKey="%s-%s" % (klass.DEFAULT_FOLDER, klass._udi_)
                        )

    def get_category(self, udi, **kwargs):
        if not self._categories.has_key(udi):
            self._categories[udi] = DataProviderCategory.DataProviderCategory(
                    kwargs['label'],
                    "drive-removable-media",
                    udi)
        return self._categories[udi]

    def get_dataproviders(self, udi, **kwargs):
         return self._volumes.get(udi,())
         
    def get_args(self, udi, **kwargs):
        return ()

