import gtk
from gettext import gettext as _
import traceback
import threading
import gobject
import time

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes as DataType
import conduit.datatypes.File as File
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils
import conduit.Settings as Settings

import gnomevfs
import os.path

MODULES = {
	"FileTwoWay" :    { "type": "dataprovider" },
	"FileConverter" : { "type": "converter" }
}

TYPE_FILE = 1
TYPE_FOLDER = 2
URI_IDX = 0
TYPE_IDX = 1
CONTAINS_NUM_IDX = 2
SCAN_COMPLETE_IDX = 3

class _FolderScanner(threading.Thread, gobject.GObject):
    """
    Recursively scans a given folder URI, returning the number of
    contained files.
    """
    __gsignals__ =  { 
                    "scan-progress": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
                        gobject.TYPE_INT]),
                    "scan-completed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])
                    }

    def __init__(self, baseURI):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.baseURI = baseURI
        self.dirs = [baseURI]
        self.cancelled = False
        self.URIs = []
        self.setName("FolderScanner Thread: %s" % baseURI)

    def run(self):
        """
        Recursively adds all files in dirs within the given list.
        
        Code adapted from Listen (c) 2006 Mehdi Abaakouk
        (http://listengnome.free.fr/)
        """
        delta = 0
        
        startTime = time.time()
        t = 1
        last_estimated = estimated = 0 
        while len(self.dirs)>0:
            if self.cancelled:
                return
            dir = self.dirs.pop(0)
            try:hdir = gnomevfs.DirectoryHandle(dir)
            except: 
                logging.warn("Folder %s Not found" % dir)
                continue
            try: fileinfo = hdir.next()
            except StopIteration: continue;
            while fileinfo:
                if fileinfo.name[0] in [".",".."]: 
                    pass
                elif fileinfo.type == gnomevfs.FILE_TYPE_DIRECTORY:
                    self.dirs.append(dir+"/"+gnomevfs.escape_string(fileinfo.name))
                    t += 1
                else:
                    try:
                        uri = gnomevfs.make_uri_canonical(dir+"/"+gnomevfs.escape_string(fileinfo.name))
                        if fileinfo.type == gnomevfs.FILE_TYPE_REGULAR:
                            self.URIs.append(uri)
                    except UnicodeDecodeError:
                        raise "UnicodeDecodeError",uri
                try: fileinfo = hdir.next()
                except StopIteration: break;
            #Calculate the estimated complete percentags
            estimated = 1.0-float(len(self.dirs))/float(t)
            estimated *= 100
            #Enly emit progress signals every 10% (+/- 1%) change to save CPU
            if delta+10 - estimated <= 1:
                logging.debug("Folder scan %s%% complete" % estimated)
                self.emit("scan-progress",len(self.URIs))
                delta += 10
            last_estimated = estimated

        i = 0
        total = len(self.URIs)
        endTime = time.time()
        #logging.debug("%s files loaded in %s seconds" % (total, (endTime - startTime)))
        self.emit("scan-completed")

    def cancel(self):
        """
        Cancels the thread as soon as possible.
        """
        self.cancelled = True

class _ScannerThreadManager:
    """
    Manages many _FolderScanner threads. This involves joining and cancelling
    said threads, and respecting a maximum num of concurrent threads limit
    """
    MAX_CONCURRENT_SCAN_THREADS = 2
    def __init__(self):
        self.scanThreads = {}
        self.pendingScanThreadsURIs = []
        self.concurrentThreads = 0

    def make_thread(self, folderURI, progressCb, completedCb, rowref):
        """
        Makes a thread for scanning folderURI. The thread callsback the model
        at regular intervals and updates rowref within that model
        """
        if folderURI not in self.scanThreads:
            thread = _FolderScanner(folderURI)
            thread.connect("scan-progress",progressCb, rowref)
            thread.connect("scan-completed",completedCb, rowref)
            self.scanThreads[folderURI] = thread
            if self.concurrentThreads < _ScannerThreadManager.MAX_CONCURRENT_SCAN_THREADS:
                logging.debug("Starting thread %s" % folderURI)
                self.scanThreads[folderURI].start()
                self.concurrentThreads += 1
            else:
                self.pendingScanThreadsURIs.append(folderURI)

    def register_thread_completed(self):
        """
        Decrements the count of concurrent threads and starts any 
        pending threads if there is space
        """
        self.concurrentThreads -= 1
        if self.concurrentThreads < _ScannerThreadManager.MAX_CONCURRENT_SCAN_THREADS:
            try:
                uri = self.pendingScanThreadsURIs.pop()
                logging.debug("Starting pending thread %s" % uri)
                self.scanThreads[uri].start()
                self.concurrentThreads -= 1
            except IndexError: pass

    def join_all_threads(self):
        """
        Joins all threads (blocks)

        Unfortunately we join all the threads do it in a loop to account
        for join() a non started thread failing. To compensate I time.sleep()
        to not smoke CPU
        """
        joinedThreads = 0
        while(joinedThreads < len(self.scanThreads)):
            for thread in self.scanThreads.values():
                try:
                    thread.join()
                    joinedThreads += 1
                except AssertionError: 
                    #deal with not started threads
                    time.sleep(1)

    def cancel_all_threads(self):
        """
        Cancels all threads ASAP. My block for a small period of time
        because we use our own cancel method
        """
        for thread in self.scanThreads.values():
            if thread.isAlive():
                logging.debug("Cancelling thread %s" % thread)
                thread.cancel()
            thread.join() #May block

class _FileSourceConfigurator(_ScannerThreadManager):
    """
    Configuration dialog for the FileTwoway dataprovider
    """
    FILE_ICON = gtk.icon_theme_get_default().load_icon("text-x-generic", 16, 0)
    FOLDER_ICON = gtk.icon_theme_get_default().load_icon("folder", 16, 0)
    def __init__(self, gladefile, mainWindow, items, unmatchedURI):
        _ScannerThreadManager.__init__(self)
        self.tree = gtk.glade.XML(conduit.GLADE_FILE, "FileTwowayConfigDialog")
        dic = { "on_addfile_clicked" : self.on_addfile_clicked,
                "on_adddir_clicked" : self.on_adddir_clicked,
                "on_remove_clicked" : self.on_remove_clicked,                
                None : None
                }
        self.tree.signal_autoconnect(dic)
        self.mainWindow = mainWindow
        self.model = items
        self.unmatchedURI = unmatchedURI

        self._make_view()

        #Now go an background scan some folders to populate the UI estimates. Do 
        #in two steps otherwise the model gets updated via cb and breaks the iter
        i = []
        for item in self.model:
            if item[TYPE_IDX] == TYPE_FOLDER and item[SCAN_COMPLETE_IDX] == False:
                i.append((item[URI_IDX],item.iter))
        for uri, rowref in i:
            self.make_thread(uri, self._on_scan_folder_progress, self._on_scan_folder_completed, rowref)

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
        column2 = gtk.TreeViewColumn("Name", nameRenderer)
        column2.set_property("expand", True)
        column2.set_cell_data_func(nameRenderer, self._item_name_data_func)
        self.view.append_column(column2)
        #Third column is the number of contained items
        containsNumRenderer = gtk.CellRendererText()
        column3 = gtk.TreeViewColumn("Items", containsNumRenderer)
        column3.set_cell_data_func(containsNumRenderer, self._item_contains_num_data_func)
        self.view.append_column(column3)

        #Config the folderchoose button when we are used as a sink
        self.folderChooserButton = self.tree.get_widget("filechooserbutton1")
        self.folderChooserButton.set_current_folder_uri(self.unmatchedURI)

        self.dlg = self.tree.get_widget("FileTwowayConfigDialog")
        self.dlg.set_transient_for(self.mainWindow)

    def _item_icon_data_func(self, column, cell_renderer, tree_model, rowref):
        """
        Draw the appropriate icon depending if the URI is a 
        folder or a file
        """
        path = self.model.get_path(rowref)
        if self.model[path][TYPE_IDX] == TYPE_FILE:
            icon = _FileSourceConfigurator.FILE_ICON
        elif self.model[path][TYPE_IDX] == TYPE_FOLDER:
            icon = _FileSourceConfigurator.FOLDER_ICON
        else:
            icon = None
        cell_renderer.set_property("pixbuf",icon)

    def _item_contains_num_data_func(self, column, cell_renderer, tree_model, rowref):
        """
        Displays the number of files contained within a folder or an empty
        string if the model item is a File
        """
        path = self.model.get_path(rowref)
        if self.model[path][TYPE_IDX] == TYPE_FILE:
            contains = ""
        elif self.model[path][TYPE_IDX] == TYPE_FOLDER:
            contains = "<i>Contains %s Files</i>" % self.model[path][CONTAINS_NUM_IDX]
        else:
            contains = "<b>ERROR</b>"
        cell_renderer.set_property("markup",contains)
        
    def _item_name_data_func(self, column, cell_renderer, tree_model, rowref):
        """
        Strips the filename from the URI and displays is
        """
        path = self.model.get_path(rowref)
        uri = self.model[path][URI_IDX]
        cell_renderer.set_property("text",Utils.get_filename(uri))

    def _on_scan_folder_progress(self, folderScanner, numItems, rowref):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        path = self.model.get_path(rowref)
        self.model[path][CONTAINS_NUM_IDX] = numItems

    def _on_scan_folder_completed(self, folderScanner, rowref):
        """
        Called when the folder scanner thread completes
        """
        logging.debug("Folder scan complete")
        path = self.model.get_path(rowref)
        self.model[path][SCAN_COMPLETE_IDX] = True
        self.register_thread_completed()

    def show_dialog(self):
        response = self.dlg.run()
        self.dlg.destroy()
        #We can actually go ahead and cancel all the threads. The items count
        #is only used as GUI bling and is recalculated in refresh() anyway
        self.cancel_all_threads()
        if response == gtk.RESPONSE_OK:
            self.unmatchedURI = self.folderChooserButton.get_uri()
        else:
            logging.warn("Cancel Not Implemented")
        
        
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
            self.model.append((fileURI,TYPE_FILE,0,False))
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
            #Scan a thread to scan the folder
            if folderURI not in self.scanThreads:
                rowref = self.model.append((folderURI,TYPE_FOLDER,0,False)) 
                self.make_thread(folderURI, self._on_scan_folder_progress, self._on_scan_folder_completed, rowref)
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
        
    def on_remove_clicked(self, *args):
        (store, rowref) = self.view.get_selection().get_selected()
        if store and rowref:
            store.remove(rowref)

class FileTwoWay(DataProvider.TwoWay, _ScannerThreadManager):

    _name_ = _("Files")
    _description_ = _("Source for synchronizing files")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "twoway"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        _ScannerThreadManager.__init__(self)
        
        #list of file and folder URIs
        self.items = gtk.ListStore(
                        gobject.TYPE_STRING,    #URI
                        gobject.TYPE_INT,       #Type (file or folder)
                        gobject.TYPE_INT,       #Number of contained items
                        gobject.TYPE_BOOLEAN    #Has the folder been scanned (i.e. is the item count accurate)
                        )
        #A dict of lists. First index is the URI, second array is metadata
        #self.URI[uri] = (type, base_path, descriptive_group_name)
        self.URIs = {}
        #When acting as a sink, place all unmatched items in here
        self.unmatchedURI = "file://"+os.path.expanduser("~")

    def initialize(self):
        return True

    def configure(self, window):
        f = _FileSourceConfigurator(conduit.GLADE_FILE, window, self.items, self.unmatchedURI)
        #FIXME: I dont do anything if the confiure operation is cancelled        
        f.show_dialog()
       
    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        #Make a whole bunch of threads to go and scan the directories
        for item in self.items:
            #Make sure we rescan
            item[SCAN_COMPLETE_IDX] = False
            if item[TYPE_IDX] == TYPE_FILE:
                fileUri = item[URI_IDX]
                self.URIs[fileUri] = (TYPE_FILE, "", "")
            elif item[TYPE_IDX] == TYPE_FOLDER:
                folderURI = item[URI_IDX]
                rowref = item.iter
                self.make_thread(folderURI, self._on_scan_folder_progress, self._on_scan_folder_completed, rowref)
            else:
                pass
        
        #All threads must complete before refresh can exit - otherwise we might
        #miss some items
        self.join_all_threads()

        #Now save the URIs that each thread got
        for thread in self.scanThreads.values():
            for i in thread.URIs:
                self.URIs[i] = (TYPE_FOLDER, thread.baseURI, "")

    def put(self, vfsFile, overwrite):
        """
        General approach involves
        """
        DataProvider.TwoWay.put(self, vfsFile, overwrite)
        if vfsFile.basePath == "":
            #The file came from a DP in which the concept of a basepath doesnt
            #make sense (like when being converted from a note etc)
            newURI = os.path.join(self.unmatchedURI, vfsFile.get_filename())
            Utils.do_gnomevfs_transfer(
                                gnomevfs.URI(vfsFile.URI), 
                                gnomevfs.URI(newURI), 
                                overwrite
                                )
        else:
            print vfsFile.URI, vfsFile.basePath
    	#This is a two way capable datasource, so it also implements the put
        #method.
        #if vfsFileOnTopOf:
        #    logging.debug("File Source: put %s -> %s" % (vfsFile.URI, vfsFileOnTopOf.URI))
        #    if vfsFile.URI != None and vfsFileOnTopOf.URI != None:
        #        #its newer so overwrite the old file
        #        Utils.do_gnomevfs_transfer(
        #            gnomevfs.URI(vfsFile.URI), 
        #            gnomevfs.URI(vfsFileOnTopOf.URI), 
        #            True
        #            )
                
    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        uri = self.URIs.keys()[index]
        typ,base,group = self.URIs[uri]
        return File.File(
                    uri=uri,
                    basepath=base
                    )

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.URIs.keys())

    def finish(self):
        self.URIs = {}

    def set_configuration(self, config):
        try:
            self.unmatchedURI = config["unmatchedURI"]
            files = config["files"]
            folders = config["folders"]
            for f in files:
                #FIXME: Hack because we PrettyPrint xml and cannot xml.dom.ext.StripXml(doc) it
                #see http://mail.python.org/pipermail/xml-sig/2004-September/010563.html
                #the solution is to ????
                if Utils.get_protocol(f) != "":
                    self.items.append((f,TYPE_FILE,0,False))
            for f in folders:
                if Utils.get_protocol(f) != "":
                    self.items.append((f,TYPE_FOLDER,0,False))
        except: pass

    def get_configuration(self):
        files = []
        folders = []
        for item in self.items:
            if item[TYPE_IDX] == TYPE_FILE:
                files.append(item[URI_IDX])
            else:
                folders.append(item[URI_IDX])
        return {"unmatchedURI" : self.unmatchedURI,
                "files" : files,
                "folders" : folders}

    def _on_scan_folder_progress(self, folderScanner, numItems, rowref):
        """
        Called by the folder scanner thread and used to update
        the estimate of the number of items in the directory
        """
        path = self.items.get_path(rowref)
        self.items[path][CONTAINS_NUM_IDX] = numItems

    def _on_scan_folder_completed(self, folderScanner, rowref):
        logging.debug("Folder scan complete %s" % folderScanner)
        path = self.items.get_path(rowref)
        self.items[path][SCAN_COMPLETE_IDX] = True
        self.register_thread_completed()

class FileConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,file" : self.text_to_file,
                            "file,text" : self.file_to_text
                            }
        
    def text_to_file(self, theText):
        return Utils.new_tempfile(str(theText))

    def file_to_text(self, thefile):
        #FIXME: Check if its a text mimetype?
        return "Text -> File"
       
