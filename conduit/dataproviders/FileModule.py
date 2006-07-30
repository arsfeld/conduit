import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.datatypes.File as File
import conduit.Exceptions as Exceptions

import gnomevfs
import os.path

MODULES = {
	"FileSource" : {
		"name": _("File Source"),
		"description": _("Source for synchronizing files"),
		"type": "source",
		"category": "Local",
		"in_type": "file",
		"out_type": "file"
	},
	"FileSink" : {
		"name": _("File Sink"),
		"description": _("Sink for synchronizing files"),
		"type": "sink",
		"category": "Local",
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
        
        #list of file URIs
        self.files = ["ssh://root@www.greenbirdsystems.com/var/www/greenbirdsystems.com/logo.png", "file:///home/john/Desktop/plaintext.txt"]
        
    def configure(self, window):
        fileStore = gtk.ListStore( str )
        for f in self.files:
            fileStore.append( [f] )
        f = FileSourceConfigurator(conduit.GLADE_FILE, window, fileStore)
        #Blocks
        f.run()
        self.files = [ r[0] for r in fileStore ]
        
    def get(self):
        for f in self.files:
            vfsFile = File.File()
            vfsFile.load_from_uri(f)
            vfsFile.get_modification_time()
            yield vfsFile
		
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

class FileConverter:
    def __init__(self):
        self.conversions =  {    
                            "text,file" : self.text_to_file,
                            "file,text" : self.file_to_text
                            }
        
    def text_to_file(self, measure):
        return "text->file = ", str(measure)

    def file_to_text(self, measure):
        return "file->text = ", str(measure)

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
            self.fileStore.append( [dialog.get_uri()] )
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
            self.fileStore.append( [dialog.get_uri()] )
            logging.debug("Selected folder %s" % dialog.get_uri())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
        
    def on_remove_clicked(self, *args):
        (store, iter) = self.fileTreeView.get_selection().get_selected()
        if store and iter:
            value = store.get_value( iter, 0 )
            store.remove( iter )        
