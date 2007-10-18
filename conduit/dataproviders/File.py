import os.path
import gtk
import gobject
import gnomevfs

import conduit
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes as DataType
import conduit.datatypes.File as File
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils

TYPE_FILE = 0
TYPE_FOLDER = 1
TYPE_EMPTY_FOLDER = 2
TYPE_SINGLE_FILE = 3

#Indexes of data in the list store
URI_IDX = 0                     #URI of the file/folder
TYPE_IDX = 1                    #TYPE_FILE/FOLDER/etc
CONTAINS_NUM_ITEMS_IDX = 2      #(folder only) How many items in the folder
SCAN_COMPLETE_IDX = 3           #(folder only) HAs the folder been recursively scanned
GROUP_NAME_IDX = 4              #(folder only) The visible identifier for the folder
CONTAINS_ITEMS_IDX = 5          #(folder only) All the items contained within the folder

CONFIG_FILE_NAME = ".conduit.conf"

def _save_config_file_for_dir(uri, groupName):
    tempFile = Utils.new_tempfile(groupName)
    tempFile.force_new_filename(CONFIG_FILE_NAME)
    tempFile.transfer(uri, True)

def _get_config_file_for_dir(uri):
    config = os.path.join(uri,CONFIG_FILE_NAME)
    return gnomevfs.read_entire_file(config)

class FileSource(DataProvider.DataSource, Utils.ScannerThreadManager):

    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        Utils.ScannerThreadManager.__init__(self)
        
        #list of file and folder URIs
        self.items = gtk.ListStore(
                        gobject.TYPE_STRING,    #URI_IDX
                        gobject.TYPE_INT,       #TYPE_IDX
                        gobject.TYPE_INT,       #CONTAINS_NUM_ITEMS_IDX
                        gobject.TYPE_BOOLEAN,   #SCAN_COMPLETE_IDX
                        gobject.TYPE_STRING,    #GROUP_NAME_IDX
                        gobject.TYPE_PYOBJECT   #CONTAINS_ITEMS_IDX
                        )
        #A dictionary of files with meta info
        self.files = {} #uri:   (basepath, groupname)

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #Make a whole bunch of threads to go and scan the directories
        for item in self.items:
            #Make sure we rescan
            item[SCAN_COMPLETE_IDX] = False
            if item[TYPE_IDX] == TYPE_SINGLE_FILE:
                self.files[item[URI_IDX]] = ( "", "" )
            else:
                folderURI = item[URI_IDX]
                rowref = item.iter
                #dont include hidden files for file source
                self.make_thread(
                        folderURI, 
                        False,  
                        self._on_scan_folder_progress, 
                        self._on_scan_folder_completed, 
                        rowref
                        )
        
        #All threads must complete before refresh can exit - otherwise we might
        #miss some items
        self.join_all_threads()

        #Now save the URIs that each thread returned
        for item in self.items:
            if item[TYPE_IDX] == TYPE_FOLDER:
                if item[CONTAINS_NUM_ITEMS_IDX] == 0:
                    self.files[item[URI_IDX]] = ( item[URI_IDX], item[GROUP_NAME_IDX] )
                else:
                    for i in item[CONTAINS_ITEMS_IDX]:
                        self.files[i] = ( item[URI_IDX], item[GROUP_NAME_IDX] )

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        basepath, group = self.files[LUID]
        f = File.File(
                    URI=        LUID,
                    basepath=   basepath,
                    group=      group
                    )
        f.set_open_URI(LUID)
        f.set_UID(LUID)
        return f

    def add(self, LUID):
        f = File.File(URI=LUID)
        if f.exists():
            for item in self.items:
                if item[URI_IDX] == f._get_text_uri():
                    conduit.logd("Could not add (already added): %s" % LUID)
                    return False

            if f.is_directory():
                conduit.logd("Adding directory: %s" % LUID)
                self.items.append((f._get_text_uri(),TYPE_FOLDER,0,False,"",[]))
            else:
                conduit.logd("Adding file: %s" % LUID)
                self.items.append((f._get_text_uri(),TYPE_SINGLE_FILE,0,False,"",[]))                
        else:
            conduit.logw("Could not add: %s" % LUID)
            return False
            
        return True

    def get_all(self):
        return self.files.keys()

    def finish(self):
        DataProvider.DataSource.finish(self)
        self.files = {}

    def set_configuration(self, config):
        for f in config.get("files",[]):
            self.items.append((f,TYPE_SINGLE_FILE,0,False,"",[]))
        for f in config.get("folders",[]):
            if Utils.get_protocol(f) != "":
                self.items.append((f,TYPE_FOLDER,0,False,"",[]))

    def get_configuration(self):
        files = []
        folders = []
        for item in self.items:
            if item[TYPE_IDX] == TYPE_SINGLE_FILE:
                files.append(item[URI_IDX])
            else:
                folders.append(item[URI_IDX])
                #If the user named the group then save this
                if item[GROUP_NAME_IDX] != "":
                    _save_config_file_for_dir(item[URI_IDX], item[GROUP_NAME_IDX])
        return {"files" : files,
                "folders" : folders}

    def get_UID(self):
        return Utils.get_user_string()

    def _on_scan_folder_progress(self, folderScanner, numItems, rowref):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        path = self.items.get_path(rowref)
        self.items[path][CONTAINS_NUM_ITEMS_IDX] = numItems

    def _on_scan_folder_completed(self, folderScanner, rowref):
        conduit.logd("Folder scan complete %s" % folderScanner)
        path = self.items.get_path(rowref)
        self.items[path][SCAN_COMPLETE_IDX] = True
        self.items[path][CONTAINS_ITEMS_IDX] = folderScanner.get_uris()
        #If the user has not yet given the folder a descriptive name then
        #check of the folder contains a .conduit file in which that name is 
        #stored (i.e. the case when the user starts the sync from a
        #saved configuration)
        if self.items[path][GROUP_NAME_IDX] == "":
            try:
                configString = _get_config_file_for_dir(folderScanner.baseURI)
                self.items[path][GROUP_NAME_IDX] = configString
            except gnomevfs.NotFoundError: pass

class FolderTwoWay(DataProvider.TwoWay):
    """
    TwoWay dataprovider for synchronizing a folder
    """

    _category_ = conduit.dataproviders.CATEGORY_FILES
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "folder"

    DEFAULT_FOLDER = os.path.expanduser("~")
    DEFAULT_GROUP = "Home"
    DEFAULT_HIDDEN = False
    DEFAULT_COMPARE_IGNORE_MTIME = False

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.need_configuration(True)

        self.folder = FolderTwoWay.DEFAULT_FOLDER
        self.folderGroupName = FolderTwoWay.DEFAULT_GROUP
        self.includeHidden = FolderTwoWay.DEFAULT_HIDDEN
        self.compareIgnoreMtime = FolderTwoWay.DEFAULT_COMPARE_IGNORE_MTIME
        self.files = []

        self._monitor_folder_id = None

    def __del__(self):
        if self._monitor_folder_id != None:
            gnomevfs.monitor_cancel(self._monitor_folder_id)
            self._monitor_folder_id = None

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        #scan the folder
        scanThread = Utils.FolderScanner(self.folder, self.includeHidden)
        scanThread.start()
        scanThread.join()

        self.files = scanThread.get_uris()

    def put(self, vfsFile, overwrite, LUID=None):
        """
        Puts vfsFile at the correct location. There are two scenarios
        1) File came from a foreign DP like tomboy
        2) File came from another file dp

        Behaviour:
        1) The foreign DP should have encoded enough information (such as
        the filename) so that we can go ahead and put the file in the dir
        2) First we see if the file has a group attribute. If so, and the
        group matches the groupName here then we put the files into the 
        directory. If not we put the file in the orphan dir. We try and 
        retain the relative path for the files in the specifed group 
        and recreate that in the group dir
        """
        DataProvider.TwoWay.put(self, vfsFile, overwrite, LUID)
        newURI = ""
        if LUID != None:
            newURI = LUID
        elif vfsFile.basePath == "":
            #came from another type of dataprovider such as tomboy
            #where relative path makes no sense. Could also come from
            #the FileSource dp when the user has selected a single file
            conduit.logd("FolderTwoWay: No basepath. Going to empty dir")
            newURI = self.folder+"/"+vfsFile.get_filename()
        else:
            pathFromBase = vfsFile._get_text_uri().replace(vfsFile.basePath,"")
            #Look for corresponding groups
            if self.folderGroupName == vfsFile.group:
                conduit.logd("FolderTwoWay: Found corresponding group")
                #put in the folder
                newURI = self.folder+pathFromBase
            else:
                conduit.logd("FolderTwoWay: Recreating group %s --- %s --- %s" % (vfsFile._get_text_uri(),vfsFile.basePath,vfsFile.group))
                #unknown. Store in the dir but recreate the group
                newURI = self.folder+"/"+vfsFile.group+pathFromBase

        destFile = File.File(URI=newURI)
        comp = vfsFile.compare(
                        destFile, 
                        sizeOnly=self.compareIgnoreMtime
                        )
        if overwrite or comp == DataType.COMPARISON_NEWER:
            vfsFile.transfer(newURI, True)

        return gnomevfs.make_uri_canonical(newURI)

    def delete(self, LUID):
        f = File.File(URI=LUID)
        if f.exists():
            f.delete()
                
    def get(self, uid):
        DataProvider.TwoWay.get(self, uid)
        f = File.File(
                    URI=uid,
                    basepath=self.folder,
                    group=self.folderGroupName
                    )
        f.set_open_URI(uid)
        f.set_UID(uid)
        return f

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return self.files

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.files = []

    def add(self, LUID):
        f = File.File(URI=LUID)
        if f.exists() and f.is_directory():
            self.folder = f._get_text_uri()
            self.set_configured(True)
            return True
        return False

    def set_configuration(self, config):
        self.folder = config.get("folder", FolderTwoWay.DEFAULT_FOLDER)
        self.folderGroupName = config.get("folderGroupName", FolderTwoWay.DEFAULT_GROUP)
        self.includeHidden = config.get("includeHidden", FolderTwoWay.DEFAULT_HIDDEN)
        self.compareIgnoreMtime = config.get("compareIgnoreMtime", FolderTwoWay.DEFAULT_COMPARE_IGNORE_MTIME)

        self.set_configured(True)
        self._monitor_folder()

    def get_configuration(self):
        _save_config_file_for_dir(self.folder, self.folderGroupName)
        return {
            "folder" : self.folder,
            "folderGroupName" : self.folderGroupName,
            "includeHidden" : self.includeHidden,
            "compareIgnoreMtime" : self.compareIgnoreMtime
            }

    def get_UID(self):
        return "%s:%s" % (self.folder, self.folderGroupName)

    def _on_scan_folder_progress(self, folderScanner, numItems, rowref):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        path = self.items.get_path(rowref)
        self.items[path][CONTAINS_NUM_ITEMS_IDX] = numItems

    def _on_scan_folder_completed(self, folderScanner, rowref):
        conduit.logd("Folder scan complete %s" % folderScanner)
        path = self.items.get_path(rowref)
        self.items[path][SCAN_COMPLETE_IDX] = True
        self.items[path][CONTAINS_ITEMS_IDX] = folderScanner.get_uris()
        #If the user has not yet given the folder a descriptive name then
        #check of the folder contains a .conduit file in which that name is 
        #stored (i.e. the case when the user starts the sync from a
        #saved configuration)
        if self.items[path][GROUP_NAME_IDX] == "":
            try:
                configString = _get_config_file_for_dir(folderScanner.baseURI)
                self.items[path][GROUP_NAME_IDX] = configString
            except gnomevfs.NotFoundError: pass

    def _monitor_folder(self):
        if self._monitor_folder_id != None:
            gnomevfs.monitor_cancel(self._monitor_folder_id)
            self._monitor_folder_id = None

        try:
            self._monitor_folder_id = gnomevfs.monitor_add(self.folder, gnomevfs.MONITOR_DIRECTORY, self._monitor_folder_cb)
        except gnomevfs.NotSupportedError:
            # silently fail if we are looking at a folder that doesn't support directory monitoring
            pass

    def _monitor_folder_cb(self, monitor_uri, event_uri, event, data=None):
        """
        Called when a file in the current folder is changed, added or deleted
        """
        # supported events = CHANGED, DELETED, STARTEXECUTING, STOPEXECUTING, CREATED, METADATA_CHANGED
        if event in (gnomevfs.MONITOR_EVENT_CREATED, gnomevfs.MONITOR_EVENT_CHANGED, gnomevfs.MONITOR_EVENT_DELETED):
            self.emit_change_detected()

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



