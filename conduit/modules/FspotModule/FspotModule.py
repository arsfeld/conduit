import os
import gobject
import dbus
import logging
log = logging.getLogger("modules.Fspot")

import conduit
import conduit.Utils as Utils
import conduit.Exceptions as Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Photo as Photo
from conduit.datatypes import Rid
import conduit.dataproviders.Image as Image

from gettext import gettext as _

MODULES = {
	"FSpotDbusTwoWay" :     { "type": "dataprovider"    },
	# "FspotSource" : { "type": "dataprovider" }
}

NAME_IDX = 0
ID_IDX = 1

# check if path exists
# PHOTO_DB = os.path.join(os.path.expanduser("~"),".gnome2", "f-spot", "photos.db")
# 
# if not os.path.exists(PHOTO_DB):
#     raise Exceptions.NotSupportedError("No F-Spot database found")
 
class FSpotDbusTwoWay(Image.ImageTwoWay):
    _name_ = _("F-Spot Photos")
    _description_ = _("Sync your F-Spot photos")
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _icon_ = "f-spot"

    SERVICE_PATH = "org.gnome.FSpot"
    PHOTOREMOTE_IFACE = "org.gnome.FSpot.PhotoRemoteControl"
    PHOTOREMOTE_PATH = "/org/gnome/FSpot/PhotoRemoteControl"

    TAGREMOTE_IFACE = "org.gnome.FSpot.TagRemoteControl"
    TAGREMOTE_PATH = "/org/gnome/FSpot/TagRemoteControl"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)

        self.enabledTags = []
        self.photos = []
        self.has_roll = False
        self.photo_remote = None
        self.tag_remote = None

        self._connect_to_fspot()
        self._hookup_signal_handlers()

    def _connect_to_fspot(self):
        bus = dbus.SessionBus()
        if Utils.dbus_service_available(FSpotDbusTwoWay.SERVICE_PATH, bus):
            if self.photo_remote == None:
                try:
                    remote_object = bus.get_object(FSpotDbusTwoWay.SERVICE_PATH, FSpotDbusTwoWay.PHOTOREMOTE_PATH)
                    self.photo_remote = dbus.Interface(remote_object, FSpotDbusTwoWay.PHOTOREMOTE_IFACE)
                except dbus.exceptions.DBusException:
                    print "*"*34
                    self.photo_remote = None

            if self.tag_remote == None:
                try:
                    remote_object = bus.get_object(FSpotDbusTwoWay.SERVICE_PATH, FSpotDbusTwoWay.TAGREMOTE_PATH)
                    self.tag_remote = dbus.Interface(remote_object, FSpotDbusTwoWay.TAGREMOTE_IFACE)
                except dbus.exceptions.DBusException:
                    print "#"*34
                    self.tag_remote = None

        #need both tag and photo remote to be OK
        return self.tag_remote != None and self.photo_remote != None

    def _hookup_signal_handlers(self):
        """
        This makes sure the photo remotes are set to none when f-spot is closed.
        """
        bus = dbus.SessionBus()
        bus.add_signal_receiver(self.handle_photoremote_down, dbus_interface=FSpotDbusTwoWay.PHOTOREMOTE_IFACE, signal_name="RemoteDown") 

    def _get_all_tags(self):
        return self.tag_remote.GetTagNames ()

    def initialize(self):
        return True
        
    def refresh(self):
        Image.ImageTwoWay.refresh(self)
        self.photos = []
        if self._connect_to_fspot():
            self.photos = self.photo_remote.Query (self.enabledTags)
        else:
            raise Exceptions.RefreshError("FSpot not available")
        
    def get_all(self):
        """
        return the list of photo id's
        """
        Image.ImageTwoWay.get_all(self)
        return [str(photo_id) for photo_id in self.photos]

    def get(self, LUID):
        """
        Get the File object for a file with a given id
        """
        Image.ImageTwoWay.get(self, LUID)

        properties = self.photo_remote.GetPhotoProperties (LUID)
        
        #FIXME: Oh python-dbus, why wont you marshall dbus.String to str...
        photouri =  str(properties['Uri'])
        tags =      str(properties['Tags']).split(',')

        f = Photo.Photo(URI=photouri)
        f.set_UID(LUID)
        f.set_open_URI(photouri)
        f.set_tags(tags)
        f.set_caption(str(properties['Description']))
        return f

    def _upload_photo (self, uploadInfo):
        """
        Import a file into the f-spot catalog
        """
        # Check if remote is read only
        if self.photo_remote.IsReadOnly ():
            raise Exceptions.SyncronizeError (_("F-Spot DBus interface is operating in read only mode"))

        # create roll if necessary
        if not self.has_roll:
            self.prepare_roll ()

        # start with enabled tags from gui, they exist in fspot for sure
        tags = list(self.enabledTags)

        # add tags from upload info
        for tag in uploadInfo.tags:
            try:
                self.tag_remote.GetTagByName (tag)
            except:
                self.tag_remote.CreateTag (tag)
            tags.append (tag)

        # import the photo
        try:
            id = self.photo_remote.ImportPhoto (uploadInfo.url, True, tags)
            return Rid(uid=str(id))
        except:
            raise Exceptions.SynchronizeError ('Import Failed')

    def delete(self, LUID):
        """
        Remove the photo from the f-spot catalog
        TODO: add support for deleting from drive also
        """
        try:
            self.photo_remote.RemovePhoto (LUID)
        except Exception, ex: # the photo is probably gone in f-spot
            log.warn("Delete failed (%s)", ex)
    
    def finish(self, aborted, error, conflict):
        """
        Round up, and don't forget the finish the import roll
        """
        Image.ImageTwoWay.finish(self)
        self.photos = []
        self.finish_roll ()

    def prepare_roll (self):
        self.photo_remote.PrepareRoll ()
        self.has_roll = True

    def finish_roll (self):
        if not self.has_roll:
            return

        self.photo_remote.FinishRoll ()
        self.has_roll = False

    def handle_photoremote_down(self):
        self.photo_remote = None
        self.tag_remote = None

    def configure(self, window):
        import gtk
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()

            model[path][1] = checked
            val = model[path][NAME_IDX]

            if checked and val not in self.enabledTags:
                self.enabledTags.append(val)
            elif not checked and val in self.enabledTags:
                self.enabledTags.remove(val)

            log.debug("Toggle '%s'(%s) to: %s" % (model[path][NAME_IDX], val, checked))
            return

        #Fspot must be running
        if not self._connect_to_fspot():
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FspotConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore(gobject.TYPE_STRING,    #NAME_IDX
                                   gobject.TYPE_BOOLEAN,   #active
                                  )
        #Fill the list store
        i = 0
        for tag in self._get_all_tags():
            list_store.append((tag,tag in self.enabledTags))
            i += 1
        #Set up the treeview
        tagtreeview.set_model(list_store)
        #column 1 is the tag name
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Tag Name"), 
                                    gtk.CellRendererText(), 
                                    text=NAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Enabled"), 
                                    renderer1, 
                                    active=1)
                                    )

        dlg = tree.get_widget("FspotConfigDialog")
        dlg.set_transient_for(window)

        response = dlg.run()
        dlg.destroy()

    def set_configuration(self, config):
        self.enabledTags = []
        for tag in config.get("tags", []):
            self.enabledTags.append(str(tag))
            
    def get_configuration(self):
        return {"tags": self.enabledTags}

    def get_UID(self):
        return Utils.get_user_string()

class FspotSource(DataProvider.DataSource):
    """
    This is the obsolete class that queried the default f-spot db
    for photos; this is now obsolete by the use of the above dbus
    based f-spot twoway dataprovider
    """
    try:
        #python 2.4
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        #python 2.5
        from sqlite3 import dbapi2 as sqlite

    _name_ = _("F-Spot Photos")
    _description_ = _("Sync your F-Spot photos")
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _module_type_ = "source"
    _in_type_ = "file/photo"
    _out_type_ = "file/photo"
    _icon_ = "f-spot"

    def __init__(self, *args):
        DataProvider.DataSource.__init__(self)
        #Settings
        self.enabledTags = []
        self.photos = []

    def _get_all_tags(self):
        tags = []
        if os.path.exists(PHOTO_DB):
            #Create a connection to the database
            con = sqlite.connect(PHOTO_DB)
            cur = con.cursor()
            #Get a list of all tags for the config dialog
            cur.execute("SELECT id, name FROM tags ORDER BY name")
            for tagid, tagname in cur:
                tags.append( (tagname,tagid) )
            con.close()

        return tags

    def initialize(self):
        return True
        
    def refresh(self):
        DataProvider.DataSource.refresh(self)
        #only work if Fspot is installed
        if not os.path.exists(PHOTO_DB):
            raise Exceptions.RefreshError("Fspot is not installed")

        #Stupid pysqlite thread stuff. 
        #Connection must be made in the same thread
        #as any execute statements
        con = sqlite.connect(PHOTO_DB)
        cur = con.cursor()

        for tagID in self.enabledTags:
            cur.execute("SELECT photo_id FROM photo_tags WHERE tag_id=%s" % (tagID))
            for photo_uid in cur:
                self.photos.append(photo_uid[0])

        con.close()

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        return self.photos

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)

        con = sqlite.connect(PHOTO_DB)
        cur = con.cursor()
        cur.execute("SELECT directory_path, name FROM photos WHERE id=?", (LUID, ))
        directory_path, name = cur.fetchone()        
        con.close()

        photouri = directory_path + "/" + name

        f = Photo.Photo(URI=photouri)
        f.set_UID(LUID)
        f.set_open_URI(photouri)

        return f
    
    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.photos = []

    def configure(self, window):
        import gtk
        def col1_toggled_cb(cell, path, model ):
            #not because we get this cb before change state
            checked = not cell.get_active()
            model[path][2] = checked
            val = model[path][ID_IDX]
            if checked and val not in self.enabledTags:
                self.enabledTags.append(val)
            elif not checked and val in self.enabledTags:
                self.enabledTags.remove(val)

            log.debug("Toggle '%s'(%s) to: %s" % (model[path][NAME_IDX], val, checked))
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FspotConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        #Build a list of all the tags
        list_store = gtk.ListStore( gobject.TYPE_STRING,    #NAME_IDX
				     gobject.TYPE_INT,       #ID_IDX
                                    gobject.TYPE_BOOLEAN,   #active
                                    )
        #Fill the list store
        i = 0
        for t in self._get_all_tags():
            list_store.append((t[NAME_IDX],t[ID_IDX],t[ID_IDX] in self.enabledTags))
            i += 1
        #Set up the treeview
        tagtreeview.set_model(list_store)
        #column 1 is the tag name
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Tag Name"), 
                                    gtk.CellRendererText(), 
                                    text=NAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Enabled"), 
                                    renderer1, 
                                    active=2)
                                    )

        dlg = tree.get_widget("FspotConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        dlg.destroy()

    def set_configuration(self, config):
        self.enabledTags = []
        for tag in config.get("tags", []):
            self.enabledTags.append(int(tag))

    def get_configuration(self):
        strTags = []
        for tag in self.enabledTags:
            strTags.append(str(tag))
        return {"tags": strTags}

    def get_UID(self):
        return Utils.get_user_string()


