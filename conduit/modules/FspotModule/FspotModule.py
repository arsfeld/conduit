import os
import gobject
import dbus
import logging
log = logging.getLogger("modules.Fspot")

import conduit
import conduit.utils as Utils
import conduit.Exceptions as Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.datatypes.Photo as Photo
from conduit.datatypes import Rid
import conduit.dataproviders.Image as Image

from gettext import gettext as _

MODULES = {
	"FSpotDbusTwoWay" :     { "type": "dataprovider"    },
}

NAME_IDX = 0
ID_IDX = 1

class FSpotDbusTwoWay(Image.ImageTwoWay):
    _name_ = _("F-Spot")
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

        self.list_store = None

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
            self._create_tag (tag)
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

    def _create_tag (self, tag):
        # Check if remote is read only
        if self.tag_remote.IsReadOnly ():
            return

        # Now see if we can create the tag
        try:
            self.tag_remote.GetTagByName (tag)
        except:
            self.tag_remote.CreateTag (tag)        

    def handle_photoremote_down(self):
        self.photo_remote = None
        self.tag_remote = None

    def configure(self, window):
        import gtk
        def create_tags_clicked_cb(button):
            text = self.tags_entry.get_text()
            if not text:
                return
            tags = text.split(',')
            for tag in tags:
                self._create_tag (tag.strip ())
            refresh_list_store()                

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

        def refresh_list_store ():
            #Build a list of all the tags
            if not self.list_store:
                self.list_store = gtk.ListStore(gobject.TYPE_STRING,    #NAME_IDX
                                                gobject.TYPE_BOOLEAN,   #active
                                               )
            else:
                self.list_store.clear ()                
            #Fill the list store
            i = 0
            for tag in self._get_all_tags():
                self.list_store.append((tag,tag in self.enabledTags))
                i += 1

        #Fspot must be running
        if not self._connect_to_fspot():
            return

        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
						"FspotConfigDialog"
						)
        tagtreeview = tree.get_widget("tagtreeview")
        refresh_list_store()
        tagtreeview.set_model(self.list_store)

        #column 1 is the tag name
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Tag Name"), 
                                    gtk.CellRendererText(), 
                                    text=NAME_IDX)
                                    )
        #column 2 is a checkbox for selecting the tag to sync
        renderer1 = gtk.CellRendererToggle()
        renderer1.set_property('activatable', True)
        renderer1.connect( 'toggled', col1_toggled_cb, self.list_store )
        tagtreeview.append_column(  gtk.TreeViewColumn(_("Enabled"), 
                                    renderer1, 
                                    active=1)
                                    )
  
        # Area for creating additional tags
        create_button = tree.get_widget ('create_button')
        self.tags_entry = tree.get_widget ('tags_entry')
        create_button.connect('clicked', create_tags_clicked_cb)

        dlg = tree.get_widget("FspotConfigDialog")
        dlg.set_transient_for(window)

        response = Utils.run_dialog (dlg, window)
        dlg.destroy()

    def set_configuration(self, config):
        self.enabledTags = []
        for tag in config.get("tags", []):
            self.enabledTags.append(str(tag))
            
    def get_configuration(self):
        return {"tags": self.enabledTags}

    def get_UID(self):
        return Utils.get_user_string()


