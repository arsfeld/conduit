import gtk
import gnomevfs
from gettext import gettext as _
import logging
log = logging.getLogger("modules.File")

import conduit
import conduit.Utils as Utils
import conduit.gtkui.Database as DB

TYPE_FILE = "0"
TYPE_FOLDER = "1"

#Indexes of data in the list store
OID_IDX = 0
URI_IDX = 1                     #URI of the file/folder
TYPE_IDX = 2                    #TYPE_FILE/FOLDER/etc
CONTAINS_NUM_ITEMS_IDX = 3      #(folder only) How many items in the folder
SCAN_COMPLETE_IDX = 4           #(folder only) HAs the folder been recursively scanned
GROUP_NAME_IDX = 5              #(folder only) The visible identifier for the folder

class _FileSourceConfigurator(Utils.ScannerThreadManager):
    """
    Configuration dialog for the FileTwoway dataprovider
    """
    FILE_ICON = gtk.icon_theme_get_default().load_icon("text-x-generic", 16, 0)
    FOLDER_ICON = gtk.icon_theme_get_default().load_icon("folder", 16, 0)
    def __init__(self, mainWindow, db):
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
        self.db = db
        self.model = DB.SqliteListStore("config", self.db)
        
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

        #Now go an background scan some folders to populate the UI estimates.
        for oid,uri in self.db.select("SELECT oid,URI FROM config WHERE TYPE=? and SCAN_COMPLETE=?",(TYPE_FOLDER,False,)):
            self.make_thread(
                    uri, 
                    False,
                    self._on_scan_folder_progress, 
                    self._on_scan_folder_completed, 
                    oid
                    )

    def _dnd_data_get(self, wid, context, x, y, selection, targetType, time):
        for uri in selection.get_uris():
            try:
                log.debug("Drag recieved %s" % uri)
                info = gnomevfs.get_file_info(uri)
                if info.type == gnomevfs.FILE_TYPE_DIRECTORY:
                    self._add_folder(uri)
                else:
                    self._add_file(uri)
            except Exception, err:
                log.debug("Error adding %s\n%s" % (uri,err))
            
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
        else:
            cell_renderer.set_property("editable", True)

    def _item_name_edited_callback(self, cellrenderertext, path, new_text):
        """
        Called when the user edits the descriptive name of the folder
        """
        self.db.update(
            table="config",
            oid=self.model[path][OID_IDX],
            GROUP_NAME=new_text
            )

    def _on_scan_folder_progress(self, folderScanner, numItems, oid):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        self.db.update(
            table="config",
            oid=oid,
            CONTAINS_NUM_ITEMS=numItems
            )

    def _on_scan_folder_completed(self, folderScanner, oid):
        """
        Called when the folder scanner thread completes
        """
        log.debug("Folder scan complete")
        self.db.update(
            table="config",
            oid=oid,
            SCAN_COMPLETE=True
            )

    def _add_folder(self, folderURI):
        """
        Adds the folder to the db. Starts a thread to scan it in the background
        """
        if folderURI not in self.scanThreads:
            oid = self.db.insert(
                        table="config",
                        values=(folderURI,TYPE_FOLDER,0,False,"")
                        )
            self.make_thread(
                    folderURI, 
                    False,
                    self._on_scan_folder_progress, 
                    self._on_scan_folder_completed, 
                    oid
                    )

    def _add_file(self, uri):
            self.db.insert(
                        table="config",
                        values=(uri,TYPE_FILE,0,False,"")
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
            self._add_file(fileURI)
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
            self._add_folder(folderURI)
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
        
    def on_remove_clicked(self, *args):
        (store, rowref) = self.view.get_selection().get_selected()
        if rowref != None:
            path = self.model.get_path(rowref)
            self.db.delete(
                table="config",
                oid=self.model[path][OID_IDX]
                )

    def on_response(self, dialog, response_id):
        """
        Called when the user clicks OK.
        """
        if response_id == gtk.RESPONSE_OK:
            #check the user has specified a named group for all folders
            count, = self.db.select_one("SELECT COUNT(oid) FROM config WHERE TYPE=? and GROUP_NAME=?", (TYPE_FOLDER,""))
            if count > 0:
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
