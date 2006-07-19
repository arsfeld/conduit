import gtk
import gobject
from gettext import gettext as _

import conduit
import logging
import DataProvider
import DataType

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
	"FileDataType" : {
		"name": _("File Data Type"),
		"description": _("Represents a file on disk"),
		"type": "datatype",
		"category": "",
		"in_type": "file",
		"out_type": "file"		
	}
	
}

class FileSource(DataProvider.DataSource):
    def __init__(self):
        DataProvider.DataSource.__init__(self, _("File Source"), _("Source for synchronizing files"))
        self.icon_name = "gtk-file"
        
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
        for f in self.files:
            yield f
		
class FileSink(DataProvider.DataSink):
    def __init__(self):
        DataProvider.DataSink.__init__(self, _("File Sink"), _("Sink for synchronizing files"))
        self.icon_name = "gtk-file"


class FileDataType(DataType.DataType):
    def __init__(self):
        DataType.DataType.__init__(self, _("File Data Type"), _("Represents a file on disk"))
        self.conversions =  {    
                            "email" : self.email_to_file,
                            "cal"   : self.cal_to_file
                            }
                            
        
    def email_to_file(self, measure):
        return str(measure) + " was a email now is a file"

    def cal_to_file(self, measure):
        return str(measure) + " was a cal now is a file"

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
        fileFilter = gtk.FileFilter()
        fileFilter.set_name(_("All files"))
        fileFilter.add_pattern("*")
        dialog.add_filter(fileFilter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.fileStore.append( [dialog.get_filename()] )
            logging.debug("Selected file %s" % dialog.get_filename())
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

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.fileStore.append( [dialog.get_filename()] )
            logging.debug("Selected folder %s" % dialog.get_filename())
        elif response == gtk.RESPONSE_CANCEL:
            pass
        dialog.destroy()
        
    def on_remove_clicked(self, *args):
        (store, iter) = self.fileTreeView.get_selection().get_selected()
        if store and iter:
            value = store.get_value( iter, 0 )
            store.remove( iter )        
