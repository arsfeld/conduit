import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes.File as File
import conduit.Exceptions as Exceptions
import conduit.Utils as Utils

import gnomevfs
import os.path

MODULES = {
	"FileSource" : {
		"name": _("File Source"),
		"description": _("Source for synchronizing files"),
		"type": "source",
		"category": DataProvider.CATEGORY_LOCAL,
		"in_type": "file",
		"out_type": "file"
	},
	"FileSink" : {
		"name": _("File Sink"),
		"description": _("Sink for synchronizing files"),
		"type": "sink",
		"category": DataProvider.CATEGORY_LOCAL,
		"in_type": "file",
		"out_type": "file"
	},
	"FileConverter" : {
		"name": _("File Data Type"),
		"description": _("Represents a file on disk"),
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": ""		
	}
	
}

class FileSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("File Source"), _("Source for synchronizing files"))
        self.icon_name = "text-x-generic"
        
        #list of file URIs (from the "add file" button
        self.files = []
        #list of folder URIs (from the "add folder" button        
        self.folders = []
        #After refresh, all folders are expanded and the files inside them
        #are added to this along with self.files
        self.allURIs = []

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
                logging.warn("%s Not found" % dir)
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
        #Join the list of discovered files from the recursive directory search
        #to the list of explicitly selected files
        self.allURIs = []
        for i in self._import_folder_real(self.folders):
            self.allURIs.append(i)
            logging.debug("Got URI %s" % i)
        for i in self.files:
            self.allURIs.append(i)
            logging.debug("Got URI %s" % i)
       
    def get(self):
        for f in self.allURIs:
            vfsFile = File.File()
            vfsFile.load_from_uri(f)
            yield vfsFile
            
    def get_configuration(self):
        return {
            "files" : self.files,
            "folders" : self.folders
            }
		
class FileSink(DataProvider.DataSink):
    DEFAULT_FOLDER_URI = os.path.expanduser("~")
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("File Sink"), _("Sink for synchronizing files"))
        self.icon_name = "text-x-generic"
        self.folderURI = FileSink.DEFAULT_FOLDER_URI
        
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
        
    def put(self, vfsfile):
        #Ok Put the files in the specified directory and retain their names
        #first check if (a converter) has given us another filename to use
        if len(vfsfile.forceNewFilename) > 0:
            filename = vfsfile.forceNewFilename
        else:
            filename = vfsfile.get_filename()
        toURI = gnomevfs.URI(os.path.join(self.folderURI, filename))
        fromURI = gnomevfs.URI(vfsfile.get_uri_string())
        try:
            #FIXME: I should probbably do something with the result returned
            #from xfer_uri
            result = gnomevfs.xfer_uri( fromURI, toURI,
                                        gnomevfs.XFER_DEFAULT,
                                        gnomevfs.XFER_ERROR_MODE_ABORT,
                                        gnomevfs.XFER_OVERWRITE_MODE_SKIP)
        except:
            raise Exceptions.SyncronizeError
            
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
