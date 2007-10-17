import gtk
from gettext import gettext as _
import gobject

import conduit
from conduit import log,logd,logw
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Module as Module
import conduit.datatypes as DataType
import conduit.datatypes.File as File
import conduit.datatypes.Text as Text
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils
import conduit.Settings as Settings

import gnomevfs
import os.path

MODULES = {
	"FileSource" :      { "type": "dataprovider" },
	"FolderTwoWay" :    { "type": "dataprovider" },
#    "USBFactory" :      { "type": "dataprovider-factory" }
}

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

class _FileSourceConfigurator(Utils.ScannerThreadManager):
    """
    Configuration dialog for the FileTwoway dataprovider
    """
    FILE_ICON = gtk.icon_theme_get_default().load_icon("text-x-generic", 16, 0)
    FOLDER_ICON = gtk.icon_theme_get_default().load_icon("folder", 16, 0)
    def __init__(self, mainWindow, items):
        Utils.ScannerThreadManager.__init__(self)
        self.tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FileSourceConfigDialog"
						)
        dic = { "on_addfile_clicked" : self.on_addfile_clicked,
                "on_adddir_clicked" : self.on_adddir_clicked,
                "on_remove_clicked" : self.on_remove_clicked,                
                None : None
                }
        self.tree.signal_autoconnect(dic)
        self.mainWindow = mainWindow
        self.model = items
        
        self._make_view()

        #setup dnd onto the file list
        targets = [ ( "text/uri-list", 0, 0 ) ]
        f = self.tree.get_widget("filesscrolledwindow")
        f.drag_dest_set(
            gtk.DEST_DEFAULT_MOTION | gtk.DEST_DEFAULT_HIGHLIGHT | gtk.DEST_DEFAULT_DROP,
            targets, 
            gtk.gdk.ACTION_COPY
            )
        f.connect("drag_data_received", self._dnd_data_get)

        self.dlg = self.tree.get_widget("FileSourceConfigDialog")
        #connect to dialog response signal because we want to validate that
        #the user has named all the groups before we let them quit
        self.dlg.connect("response",self.on_response)
        self.dlg.set_transient_for(self.mainWindow)
        self.dlg.show_all()

        #Now go an background scan some folders to populate the UI estimates. Do 
        #in two steps otherwise the model gets updated via cb and breaks the iter
        i = []
        for item in self.model:
            if item[TYPE_IDX] == TYPE_FOLDER and item[SCAN_COMPLETE_IDX] == False:
                i.append((item[URI_IDX],item.iter))
        for uri, rowref in i:
            self.make_thread(uri, 
                        False,
                        self._on_scan_folder_progress, 
                        self._on_scan_folder_completed, 
                        rowref
                        )

    def _dnd_data_get(self, wid, context, x, y, selection, targetType, time):
        for uri in selection.get_uris():
            try:
                logd("Drag recieved %s" % uri)
                info = gnomevfs.get_file_info(uri)
                if info.type == gnomevfs.FILE_TYPE_DIRECTORY:
                    self._add_directory(uri)
                else:
                    self.model.append((uri,TYPE_SINGLE_FILE,0,False,"",[]))
            except Exception, err:
                logd("Error adding %s\n%s" % (uri,err))
            
    def _make_view(self):
        """
        Creates the treeview and connects the model and appropriate
        cell_data_funcs
        """
        #Config the treeview when the DP is used as a source
        self.view = self.tree.get_widget("treeview1")
        self.view.set_model( self.model )
        #First column is an icon (folder of File)
        iconRenderer = gtk.CellRendererPixbuf()
        column1 = gtk.TreeViewColumn("Icon", iconRenderer)
        column1.set_cell_data_func(iconRenderer, self._item_icon_data_func)
        self.view.append_column(column1)
        #Second column is the File/Folder name
        nameRenderer = gtk.CellRendererText()
        nameRenderer.connect('edited', self._item_name_edited_callback)
        column2 = gtk.TreeViewColumn("Name", nameRenderer)
        column2.set_property("expand", True)
        column2.set_cell_data_func(nameRenderer, self._item_name_data_func)
        self.view.append_column(column2)
        #Third column is the number of contained items
        containsNumRenderer = gtk.CellRendererText()
        column3 = gtk.TreeViewColumn("Items", containsNumRenderer)
        column3.set_cell_data_func(containsNumRenderer, self._item_contains_num_data_func)
        self.view.append_column(column3)

    def _item_icon_data_func(self, column, cell_renderer, tree_model, rowref):
        """
        Draw the appropriate icon depending if the URI is a 
        folder or a file. We only show single files in the GUI anyway
        """
        path = self.model.get_path(rowref)
        if self.model[path][TYPE_IDX] == TYPE_FILE:
            icon = _FileSourceConfigurator.FILE_ICON
        elif self.model[path][TYPE_IDX] == TYPE_SINGLE_FILE:
            icon = _FileSourceConfigurator.FILE_ICON
        else:
            icon = _FileSourceConfigurator.FOLDER_ICON
        cell_renderer.set_property("pixbuf",icon)

    def _item_contains_num_data_func(self, column, cell_renderer, tree_model, rowref):
        """
        Displays the number of files contained within a folder or an empty
        string if the model item is a File
        """
        path = self.model.get_path(rowref)
        if self.model[path][TYPE_IDX] == TYPE_FILE:
            contains = ""
        elif self.model[path][TYPE_IDX] == TYPE_SINGLE_FILE:
            contains = ""
        else:
            contains = "<i>Contains %s Files</i>" % self.model[path][CONTAINS_NUM_ITEMS_IDX]
        cell_renderer.set_property("markup",contains)
        
    def _item_name_data_func(self, column, cell_renderer, tree_model, rowref):
        """
        If the user has set a descriptive name for the folder the display that,
        otherwise display the filename. 
        """
        path = self.model.get_path(rowref)
        uri = self.model[path][URI_IDX]

        if self.model[path][GROUP_NAME_IDX] != "":
            displayName = self.model[path][GROUP_NAME_IDX]
        else:
            displayName = gnomevfs.format_uri_for_display(uri)

        cell_renderer.set_property("text", displayName)
        cell_renderer.set_property("ellipsize", True)

        #Can not edit the group name of a file
        if self.model[path][TYPE_IDX] == TYPE_FILE:
            cell_renderer.set_property("editable", False)
        elif self.model[path][TYPE_IDX] == TYPE_SINGLE_FILE:
            cell_renderer.set_property("editable", False)
        else:
            cell_renderer.set_property("editable", True)

    def _item_name_edited_callback(self, cellrenderertext, path, new_text):
        """
        Called when the user edits the descriptive name of the folder
        """
        self.model[path][GROUP_NAME_IDX] = new_text

    def _on_scan_folder_progress(self, folderScanner, numItems, rowref):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        path = self.model.get_path(rowref)
        self.model[path][CONTAINS_NUM_ITEMS_IDX] = numItems

    def _on_scan_folder_completed(self, folderScanner, rowref):
        """
        Called when the folder scanner thread completes
        """
        logd("Folder scan complete")
        path = self.model.get_path(rowref)
        self.model[path][SCAN_COMPLETE_IDX] = True
        self.model[path][CONTAINS_ITEMS_IDX] = folderScanner.get_uris()
        #If the user has not yet given the folder a descriptive name then
        #check of the folder contains a .conduit file in which that name is 
        #stored
        try:
            configString = _get_config_file_for_dir(folderScanner.baseURI)
            self.model[path][GROUP_NAME_IDX] = configString
        except gnomevfs.NotFoundError: pass

    def _add_directory(self, folderURI):
        """
        Adds the directory to the db. Starts a thread to scan it in the background
        """
        if folderURI not in self.scanThreads:
            rowref = self.model.append((folderURI,TYPE_FOLDER,0,False,"",[])) 
            self.make_thread(
                    folderURI, 
                    False,
                    self._on_scan_folder_progress, 
                    self._on_scan_folder_completed, 
                    rowref
                    )


    def show_dialog(self):
        response = self.dlg.run()
        #We can actually go ahead and cancel all the threads. The items count
        #is only used as GUI bling and is recalculated in refresh() anyway
        self.cancel_all_threads()

        self.dlg.destroy()
        return response
        
    def on_addfile_clicked(self, *args):
        dialog = gtk.FileChooserDialog( _("Include file ..."),  
                                        None, 
                                        gtk.FILE_CHOOSER_ACTION_OPEN,
                                        (gtk.STOCK_CANCEL, 
                                        gtk.RESPONSE_CANCEL, 
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK)
                                        )
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_local_only(False)
        fileFilter = gtk.FileFilter()
        fileFilter.set_name(_("All files"))
        fileFilter.add_pattern("*")
        dialog.add_filter(fileFilter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            fileURI = dialog.get_uri()
            self.model.append((fileURI,TYPE_SINGLE_FILE,0,False,"",[]))
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_adddir_clicked(self, *args):
        dialog = gtk.FileChooserDialog( _("Include folder ..."), 
                                        None, 
                                        gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, 
                                        (gtk.STOCK_CANCEL, 
                                        gtk.RESPONSE_CANCEL, 
                                        gtk.STOCK_OPEN, 
                                        gtk.RESPONSE_OK)
                                        )
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_local_only(False)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            folderURI = dialog.get_uri()
            self._add_directory(folderURI)
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
        
    def on_remove_clicked(self, *args):
        (store, rowref) = self.view.get_selection().get_selected()
        if store and rowref:
            store.remove(rowref)

    def on_response(self, dialog, response_id):
        """
        Called when the user clicks OK.
        """
        if response_id == gtk.RESPONSE_OK:
            #check the user has specified a named group for all folders
            for item in self.model:
                if item[TYPE_IDX] == TYPE_FOLDER or item[TYPE_IDX] == TYPE_FOLDER:
                    if item[GROUP_NAME_IDX] == "":
                        #stop this dialog from closing, and show a warning to the
                        #user indicating that all folders must be named
                        warning = gtk.MessageDialog(
                                        parent=dialog,
                                        flags=gtk.DIALOG_MODAL, 
                                        type=gtk.MESSAGE_WARNING, 
                                        buttons=gtk.BUTTONS_OK, 
                                        message_format="Please Name All Folders")
                        warning.format_secondary_text("All folders require a descriptive name. To name a folder simply click on it")
                        warning.run()
                        warning.destroy()
                        dialog.emit_stop_by_name("response")

class FileSource(DataProvider.DataSource, Utils.ScannerThreadManager):

    _name_ = _("Files")
    _description_ = _("Source for synchronizing multiple files")
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

    def configure(self, window):
        f = _FileSourceConfigurator(window, self.items)
        response = f.show_dialog()
       
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
                    logd("Could not add (already added): %s" % LUID)
                    return False

            if f.is_directory():
                logd("Adding directory: %s" % LUID)
                self.items.append((f._get_text_uri(),TYPE_FOLDER,0,False,"",[]))
            else:
                logd("Adding file: %s" % LUID)
                self.items.append((f._get_text_uri(),TYPE_SINGLE_FILE,0,False,"",[]))                
        else:
            logw("Could not add: %s" % LUID)
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
        logd("Folder scan complete %s" % folderScanner)
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

class _FolderTwoWayConfigurator:
    def __init__(self, mainWindow, folder, folderGroupName, includeHidden, compareIgnoreMtime):
        self.folder = folder
        self.includeHidden = includeHidden
        self.folderGroupName = folderGroupName
        self.compareIgnoreMtime = compareIgnoreMtime

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FolderTwoWayConfigDialog"
						)
        self.folderChooser = tree.get_widget("filechooserbutton1")
        self.folderChooser.set_uri(self.folder)
        self.folderEntry = tree.get_widget("entry1")
        self.folderEntry.set_text(self.folderGroupName)
        self.hiddenCb = tree.get_widget("hidden")
        self.hiddenCb.set_active(includeHidden)
        self.mtimeCb = tree.get_widget("ignoreMtime")
        self.mtimeCb.set_active(self.compareIgnoreMtime)

        self.dlg = tree.get_widget("FolderTwoWayConfigDialog")
        self.dlg.connect("response",self.on_response)
        self.dlg.set_transient_for(mainWindow)

    def on_response(self, dialog, response_id):
        if response_id == gtk.RESPONSE_OK:
            if self.folderEntry.get_text() == "":
                #stop this dialog from closing, and show a warning to the
                #user indicating that the folder must be named
                warning = gtk.MessageDialog(
                                parent=dialog,
                                flags=gtk.DIALOG_MODAL, 
                                type=gtk.MESSAGE_WARNING, 
                                buttons=gtk.BUTTONS_OK, 
                                message_format="Please Enter a Folder Name")
                warning.format_secondary_text("All folders require a descriptive name. To name a folder enter its name where indicated")
                warning.run()
                warning.destroy()
                dialog.emit_stop_by_name("response")
            else:
                self.folderGroupName = self.folderEntry.get_text()
                uri = self.folderChooser.get_uri()
                self.folder = gnomevfs.make_uri_canonical(uri)
                self.includeHidden = self.hiddenCb.get_active()
                self.compareIgnoreMtime = self.mtimeCb.get_active()

    def show_dialog(self):
        self.dlg.show_all()
        self.dlg.run()
        self.dlg.destroy()
        return self.folder, self.folderGroupName, self.includeHidden, self.compareIgnoreMtime


class FolderTwoWay(DataProvider.TwoWay):
    """
    TwoWay dataprovider for synchronizing a folder
    """

    _name_ = _("Folder")
    _description_ = _("Synchronize folders")
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

    def configure(self, window):
        #get its name
        try:
            self.folderGroupName = _get_config_file_for_dir(self.folder)
        except gnomevfs.NotFoundError: pass

        f = _FolderTwoWayConfigurator(window, self.folder, self.folderGroupName, self.includeHidden, self.compareIgnoreMtime)
        self.folder, self.folderGroupName, self.includeHidden, self.compareIgnoreMtime = f.show_dialog()
        self.set_configured(True)
        self._monitor_folder()
        
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
            logd("FolderTwoWay: No basepath. Going to empty dir")
            newURI = self.folder+"/"+vfsFile.get_filename()
        else:
            pathFromBase = vfsFile._get_text_uri().replace(vfsFile.basePath,"")
            #Look for corresponding groups
            if self.folderGroupName == vfsFile.group:
                logd("FolderTwoWay: Found corresponding group")
                #put in the folder
                newURI = self.folder+pathFromBase
            else:
                logd("FolderTwoWay: Recreating group %s --- %s --- %s" % (vfsFile._get_text_uri(),vfsFile.basePath,vfsFile.group))
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
        logd("Folder scan complete %s" % folderScanner)
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



