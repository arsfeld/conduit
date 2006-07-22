import gtk
import gobject
from gettext import gettext as _

import conduit
import logging
from conduit.datatypes import DataType

import DataProvider
import conduit.datatypes.File as File

import gnomevfs

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
        self.files = []
        
    def configure(self, window):
        fileStore = gtk.ListStore( str )
        for f in self.files:
            fileStore.append( [f] )
        f = FileSourceConfigurator(conduit.GLADE_FILE, window, fileStore)
        #Blocks
        f.run()
        self.files = [ r[0] for r in fileStore ]
        
    def get(self):
        DataProvider.DataProviderBase.get(self)        
        for f in self.files:
            vfsFile = File.File()
            vfsFile.load_from_uri(f)
            yield vfsFile
		
class FileSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("File Sink"), _("Sink for synchronizing files"))
        self.icon_name = "text-x-generic"
        
    def put(self, vfsfile):
        DataProvider.DataProviderBase.put(self, vfsfile)            
        #gnomevfs.xfer_uri( inuri, outuri,
        #                   gnomevfs.XFER_DEFAULT,
        #                   gnomevfs.XFER_ERROR_MODE_ABORT,
        #                   gnomevfs.XFER_OVERWRITE_MODE_SKIP)

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
            logging.debug("OK")
            pass
        elif response == gtk.RESPONSE_CANCEL:
            logging.debug("CANCEL")        
            pass
        else:
            logging.debug("DUNNO")
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
