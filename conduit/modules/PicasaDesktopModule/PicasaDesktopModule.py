import os
import csv 
import logging
import xml.dom.minidom
log = logging.getLogger("modules.Picasa")

import conduit
import conduit.Utils as Utils
import conduit.Vfs as Vfs
import conduit.Exceptions as Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Photo as Photo

from gettext import gettext as _

MODULES = {
	"PicasaDesktopSource" : { "type": "dataprovider" }
}

FILENAME_IDX = 0
DISPLAYNAME_IDX = 1
PHOTOS_IDX = 2
PICASA_DIR = os.path.join(os.path.expanduser("~"),".picasa")

# check if path exists
if not os.path.exists(PICASA_DIR):
    raise Exceptions.NotSupportedError("Picasa Not Installed")

class PicasaDesktopSource(DataProvider.DataSource):

    _name_ = _("Picasa Desktop")
    _description_ = _("Sync your Picasa photos")
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _module_type_ = "source"
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"
    _icon_ = "picasa"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        self.need_configuration(False)
        self.albums = []
        self.enabledAlbums = []
        
    def _fix_picasa_image_filename(self, filename):
        #Picasa stores the image filename in some weird relative format
        #with $ = $HOME and $My Pictures = xdg pictures dir
        parts = filename.split("\\")
        if parts[0] == "$My Pictures":
            #FIXME: Use xdg user dirs to get localised photo dir
            parts[0] = os.path.join(os.environ['HOME'],'Pictures')
        elif parts[0][0] == "$":
            #Take care of other photos in ~ by replacing $ with $HOME
            parts[0] = os.path.join(os.environ['HOME'],parts[0][1:])
        elif parts[0] == "[z]":
            #absolute paths
            parts[0] = "/"
        else:
            log.warn("Could not convert picasa photo path to unix path")
            return None
            
        path = os.path.abspath(os.sep.join(parts))
        return path            
            
    def _get_all_albums(self):
        #only work if picasa has been configured to use a CSV DB
        #http://www.zmarties.com/picasa/
        dbfile = os.path.join(PICASA_DIR,'drive_c','Program Files','Picasa2','db','dirscanner.csv')
        if not os.path.exists(dbfile):
            raise Exceptions.RefreshError("Picasa Not Configured to use CSV Database")    
    
        pals = []
        #Open the CSV file and find all entries with Type = 19 (albums)
        f = open(dbfile, 'rt')
        try:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Type'] == '19':
                    #wine picasa stores all pal files (that describes an album)
                    #in the following base dir
                    parts = [PICASA_DIR,
                            'drive_c',
                            'Documents and Settings',
                            os.getlogin(),
                            'Local Settings']
                    #and then as given in the csv file
                    #but first change the windows path to a linux one
                    parts += row['Name'].split("\\")
                    path = os.path.abspath(os.sep.join(parts))
                    pals.append(path)
        finally:
            f.close()
            
        #parse each pal file to get album info
        albums = []
        for pal in pals:
            log.debug("Parsing album file %s" % pal)
            doc = xml.dom.minidom.parse(pal)
            #album name
            for prop in doc.getElementsByTagName('property'):
                if prop.hasAttribute("name") and prop.getAttribute("name") == "name":
                    name = prop.getAttribute("value")
            #image filenames
            photos = []
            for f in doc.getElementsByTagName('filename'):
                filename = self._fix_picasa_image_filename(f.firstChild.data)
                if filename != None:
                    photos.append(filename)
            
            albums.append((
                        pal,            #FILENAME_IDX
                        name,           #DISPLAYNAME_IDX 
                        photos))        #PHOTOS_IDX
        
        return albums
        
    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        self.albums = []
        try:
            self.albums = self._get_all_albums()
        except: 
            #re-raise the refresh error
            raise
            
        print self.albums
            
    def get_all(self):
        DataProvider.DataSource.get_all(self)
        photos = []
        for album in self.albums:
            if album[FILENAME_IDX] in self.enabledAlbums:
                for photouri in album[PHOTOS_IDX]:
                    if Vfs.uri_exists(photouri):
                        photos.append(photouri)
        return photos
        
    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        f = Photo.Photo(URI=LUID)
        f.set_UID(LUID)
        f.set_open_URI(LUID)
        return f

    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.albums = []

    def configure(self, window):
        import gobject
        import gtk
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][2] = checked
            val = model[path][FILENAME_IDX]
            if checked and val not in self.enabledAlbums:
                self.enabledAlbums.append(val)
            elif not checked and val in self.enabledAlbums:
                self.enabledAlbums.remove(val)

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"PicasaDesktopConfigDialog"
						)
        tagtreeview = tree.get_widget("albumtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_STRING,    #FILENAME_IDX
                                    gobject.TYPE_STRING,    #DISLAYNAME_IDX
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store
        for t in self._get_all_albums():
            list_store.append((
                        t[FILENAME_IDX],
                        t[DISPLAYNAME_IDX],
                        t[FILENAME_IDX] in self.enabledAlbums)
                        )
        #Set up the treeview
        tagtreeview.set_model(list_store)
        #column 1 is the album name
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Album Name"), 
                                    gtk.CellRendererText(), 
                                    text=DISPLAYNAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the album to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Enabled"), 
                                    renderer1, 
                                    active=2)
                                    )

        dlg = tree.get_widget("PicasaDesktopConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.set_configured(True)
        dlg.destroy()
        
        print self.enabledAlbums

    def get_configuration(self):
        return {"enabledAlbums": self.enabledAlbums}

    def get_UID(self):
        return Utils.get_user_string()


