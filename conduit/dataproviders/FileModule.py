import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes as DataType
import conduit.datatypes.File as File
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils

import gnomevfs
import os.path

MODULES = {
	"FileSource" :    { "type": "dataprovider" },
	"FileSink" :      { "type": "dataprovider" },
	"FileConverter" : { "type": "converter" }
}

def do_gnomevfs_transfer(sourceURI, destURI, overwrite=False):
    """
    Xfers a file from fromURI to destURI. Overwrites if commanded.
    @raise Exception: if anything goes wrong in xfer
    """
    logging.debug("Transfering file from %s -> %s (Overwrite: %s)" % (sourceURI, destURI, overwrite))
    if overwrite:
        mode = gnomevfs.XFER_OVERWRITE_MODE_REPLACE
    else:
        mode = gnomevfs.XFER_OVERWRITE_MODE_SKIP
        
    #FIXME: I should probbably do something with the result returned
    #from xfer_uri
    result = gnomevfs.xfer_uri( sourceURI, destURI,
                                gnomevfs.XFER_DEFAULT,
                                gnomevfs.XFER_ERROR_MODE_ABORT,
                                mode)
    
class FileSource(DataProvider.DataSource):

    _name_ = _("File Source")
    _description_ = _("Source for synchronizing files")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "source"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        
        #list of file URIs (from the "add file" button
        self.files = []
        #list of folder URIs (from the "add folder" button        
        self.folders = []
        #After refresh, all folders are expanded and the files inside them
        #are added to this along with self.files
        self.allURIs = None

    def initialize(self):
        return True

    def _import_folder_real(self, dirs):
        """
        Recursively adds all files in dirs within the given list.
        
        Code adapted from Listen (c) 2006 Mehdi Abaakouk
        (http://listengnome.free.fr/)
        
        @param dirs: List of dirs to descend into
        @type dirs: C{string[]}
        """
        from time import time
        
        startTime = time()
        added = []
        t = 1
        last_estimated = estimated = 0 
                    
        while len(dirs)>0:
            dir = dirs.pop(0)
            try:hdir = gnomevfs.DirectoryHandle(dir)
            except: 
                logging.warn("Folder %s Not found" % dir)
                continue
            try: fileinfo = hdir.next()
            except StopIteration: continue;
            while fileinfo:
                if fileinfo.name[0] in [".",".."] or fileinfo.flags != gnomevfs.FILE_FLAGS_LOCAL: 
                    pass
                elif fileinfo.type == gnomevfs.FILE_TYPE_DIRECTORY:
                    dirs.append(dir+"/"+gnomevfs.escape_string(fileinfo.name))
                    t += 1
                else:
                    try:
                        uri = gnomevfs.make_uri_canonical(dir+"/"+gnomevfs.escape_string(fileinfo.name))
                        if fileinfo.type == gnomevfs.FILE_TYPE_REGULAR: # and READ_EXTENTIONS.has_key(utils.get_ext(uri)):
                            added.append(uri)
                    except UnicodeDecodeError:
                        raise "UnicodeDecodeError",uri
                try: fileinfo = hdir.next()
                except StopIteration: break;
            estimated = 1.0-float(len(dirs))/float(t)
            #yield max(estimated,last_estimated),False
            #print "Estimated Completion % ", max(estimated,last_estimated)
            last_estimated = estimated

        i = 0
        total = len(added)
        endTime = time()
        logging.debug("%s files loaded in %s seconds" % (total, (endTime - startTime)))
        
        #Eventually fold this method into the refresh method. Then it can 
        #retur a generator saying the completion percentage to the main app
        #for drawing a pretty % conplete graph (as this step might take a long
        #time
        return added
            
    def configure(self, window):
        fileStore = gtk.ListStore(str, str)
        for f in self.files:
            fileStore.append( [f, "File"] )
        for f in self.folders:
            fileStore.append( [f, "Folder"] )            
        f = FileSourceConfigurator(conduit.GLADE_FILE, window, fileStore)
        #Blocks
        f.run()
        #Now split out the files and folders (folders get descended into in
        #the refresh() method
        self.files = [ r[0] for r in fileStore if r[1] == "File" ]
        self.folders = [ r[0] for r in fileStore if r[1] == "Folder" ]
       
    def refresh(self):
        DataProvider.DataSource.refresh(self)

        #Join the list of discovered files from the recursive directory search
        #to the list of explicitly selected files
        self.allURIs = []
        for i in self._import_folder_real(self.folders):
            self.allURIs.append(i)
            logging.debug("Got URI %s" % i)
        for i in self.files:
            self.allURIs.append(i)
            logging.debug("Got URI %s" % i)
            
    def put(self, vfsFile, vfsFileOnTopOf=None):
	DataProvider.DataSink.put(self, vfsFile, vfsFileOnTopOf)        
	#This is a two way capable datasource, so it also implements the put
        #method.
        if vfsFileOnTopOf:
            logging.debug("File Source: put %s -> %s" % (vfsFile.URI, vfsFileOnTopOf.URI))
            if vfsFile.URI != None and vfsFileOnTopOf.URI != None:
                #its newer so overwrite the old file
                do_gnomevfs_transfer(
                    gnomevfs.URI(vfsFile.URI), 
                    gnomevfs.URI(vfsFileOnTopOf.URI), 
                    True
                    )
                
    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return File.File(self.allURIs[index])

    def get_num_items(index):
        DataProvider.DataSource.get_num_items(self)
        return len(self.allURIs)

    def finish(self):
        self.allURIs = None
            
    def get_configuration(self):
        return {
            "files" : self.files,
            "folders" : self.folders
            }
		
class FileSink(DataProvider.DataSink):

    _name_ = _("File Sink")
    _description_ = _("Sink for synchronizing files")
    _category_ = DataProvider.CATEGORY_LOCAL
    _module_type_ = "sink"
    _in_type_ = "file"
    _out_type_ = "file"
    _icon_ = "text-x-generic"

    DEFAULT_FOLDER_URI = os.path.expanduser("~")

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        self.folderURI = FileSink.DEFAULT_FOLDER_URI

    def initialize(self):
        return True
        
    def configure(self, window):
        tree = gtk.glade.XML(conduit.GLADE_FILE, "FileSinkConfigDialog")
        
        #get a whole bunch of widgets
        folderChooserButton = tree.get_widget("folderchooser")
        
        #preload the widgets
        folderChooserButton.set_current_folder_uri(self.folderURI)
            
        dlg = tree.get_widget("FileSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            self.folderURI = folderChooserButton.get_uri()
        dlg.destroy()            
        
    def put(self, vfsFile, vfsFileOnTopOf=None):
        DataProvider.DataSink.put(self, vfsFile, vfsFileOnTopOf)
        sourceURIString = vfsFile.get_uri_string()
        #Ok Put the files in the specified directory and retain their names
        #first check if (a converter) has given us another filename to use
        if len(vfsFile.forceNewFilename) > 0:
            filename = vfsFile.forceNewFilename
        else:
            filename = vfsFile.get_filename()
        destURIString = os.path.join(self.folderURI, filename)
        destFile = File.File(destURIString)
        #compare vfsFile with its destination path. if vfsFile is newer than
        #destination then overwrite it.
        comparison = destFile.compare(vfsFile, destFile)
        logging.debug("File Sink: Put %s -> %s (Comparison: %s)" % (sourceURIString, destURIString, comparison))
        if comparison == DataType.COMPARISON_NEWER:
            try:
                #its newer so overwrite the old file
                do_gnomevfs_transfer(
                    gnomevfs.URI(sourceURIString), 
                    gnomevfs.URI(destURIString), 
                    True
                    )
            except:
                raise Exceptions.SyncronizeError
        elif comparison == DataType.COMPARISON_EQUAL:
            #dont bother copying if the files are the same
            pass
        else:
            raise Exceptions.SynchronizeConflictError(comparison, vfsFile, destFile)
            
    def get_configuration(self):
        return {"folderURI" : self.folderURI}

class FileConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,file" : self.text_to_file,
                            "file,text" : self.file_to_text
                            }
        
    def text_to_file(self, theText):
        return File.new_from_tempfile(theText)

    def file_to_text(self, thefile):
        #FIXME: Check if its a text mimetype?
        return "Text -> File"

class FileSourceConfigurator:
    def __init__(self, gladefile, mainWindow, fileStore):
        tree = gtk.glade.XML(conduit.GLADE_FILE, "FileSourceConfigDialog")
        dic = { "on_addfile_clicked" : self.on_addfile_clicked,
                "on_adddir_clicked" : self.on_adddir_clicked,
                "on_remove_clicked" : self.on_remove_clicked,                
                None : None
                }
        tree.signal_autoconnect(dic)
        
        self.oldStore = fileStore
        
        self.fileStore = fileStore
        self.fileTreeView = tree.get_widget("fileTreeView")
        self.fileTreeView.set_model( self.fileStore )
        self.fileTreeView.append_column(gtk.TreeViewColumn('Name', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )                
                
        self.dlg = tree.get_widget("FileSourceConfigDialog")
        self.dlg.set_transient_for(mainWindow)
    
    def run(self):
        response = self.dlg.run()
        if response == gtk.RESPONSE_OK:
            pass
        else:
            self.fileStore = self.oldStore
        self.dlg.destroy()        
        
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
            self.fileStore.append( [dialog.get_uri(), "File"] )
            logging.debug("Selected file %s" % dialog.get_uri())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()

    def on_adddir_clicked(self, *args):
        #Its not worth bothering to implement this yet until I
        #work out a way to store and communicate the base path of this
        #added dir to the corresponding sink funtion. Otherwise
        #I cannot recreate the relative path of dirs so this function is
        #useless
        logging.info("NOT IMPLEMENTED")
        return
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
            self.fileStore.append( [dialog.get_uri(), "Folder"] )
            logging.debug("Selected folder %s" % dialog.get_uri())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
        
    def on_remove_clicked(self, *args):
        (store, iter) = self.fileTreeView.get_selection().get_selected()
        if store and iter:
            value = store.get_value( iter, 0 )
            store.remove( iter )        
