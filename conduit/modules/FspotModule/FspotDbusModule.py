import os
import gobject
import dbus
import logging
log = logging.getLogger("modules.Fspot")

import conduit
import conduit.Utils as Utils
import conduit.Exceptions
import conduit.dataproviders.DataProvider as DataProvider
import conduit.dataproviders.Image as Image
from conduit.datatypes import Rid
import conduit.datatypes.Photo as Photo

from gettext import gettext as _

MODULES = {
	"FSpotFactory" : { "type": "dataprovider-factory" }
}

NAME_IDX = 0

SERVICE_PATH = "org.gnome.FSpot"
PHOTOREMOTE_IFACE = "org.gnome.FSpot.PhotoRemoteControl"
PHOTOREMOTE_PATH = "/org/gnome/FSpot/PhotoRemoteControl"

TAGREMOTE_IFACE = "org.gnome.FSpot.TagRemoteControl"
TAGREMOTE_PATH = "/org/gnome/FSpot/TagRemoteControl"

def _get_photoremote():
    bus = dbus.SessionBus()

    try:
        remote_object = bus.get_object(SERVICE_PATH, PHOTOREMOTE_PATH)
        return dbus.Interface(remote_object, PHOTOREMOTE_IFACE)
    except dbus.exceptions.DBusException:
        return None

def _get_tagremote():
    bus = dbus.SessionBus()

    try:
        remote_object = bus.get_object(SERVICE_PATH, TAGREMOTE_PATH)
        return dbus.Interface(remote_object, TAGREMOTE_IFACE)
    except dbus.exceptions.DBusException:
        return None

class FSpotDbusTwoWay(Image.ImageTwoWay):
    _name_ = _("F-Spot DBus Photos")
    _description_ = _("Sync your F-Spot photos over DBus")
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _icon_ = "f-spot"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)
        self.need_configuration(True)

        try:
            # get photo remote control
            self.photo_remote = _get_photoremote()

            # get tag remote control
            self.tag_remote = _get_tagremote()
        except:
            print _("Failed to get remotes")

        #Settings
        self.enabledTags = []
        self.photos = []
        self.has_roll = False

    def _get_all_tags(self):
        return self.tag_remote.GetTagNames ()

    def initialize(self):
        return True
        
    def refresh(self):
        Image.ImageTwoWay.refresh(self)

        # get ids
        self.photos = self.photo_remote.Query (self.enabledTags)

    def get_all(self):
        """
        return the list of photo id's
        """
        Image.ImageTwoWay.get_all(self)
        return list (str(photo_id) for photo_id in self.photos)

    def get(self, LUID):
        """
        Get the File object for a file with a given id
        """
        Image.ImageTwoWay.get(self, LUID)

        properties = self.photo_remote.GetPhotoProperties (LUID)

        photouri = properties['Uri']
        name = str(properties['Name'])
        tags = properties['Tags'].split(',')

        f = Photo.Photo(URI=photouri)
        f.set_UID(LUID)
        f.set_open_URI(photouri)
        f.force_new_filename (name)
        f.set_tags (tags)

        return f

    def _upload_photo (self, uploadInfo):
        """
        Import a file into the f-spot catalog
        """
        # Check if remote is read only
        if self.photo_remote.IsReadOnly ():
            raise conduit.Exceptions.SyncronizeError (_("F-Spot DBus interface is operating in read only mode"))

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
                self.tag_remote.CreateTag (fspot_tag)

            tags.append (tag)

        # import the photo
        try:
            id = self.photo_remote.ImportPhoto (uploadInfo.url, True, tags)
            return Rid(uid=str(id))
        except:
            raise conduit.Exceptions.SynchronizeError ('Import Failed')

    def delete(self, LUID):
        """
        Remove the photo from the f-spot catalog
        TODO: add support for deleting from drive also
        """
        self.photo_remote.RemovePhoto (LUID)
    
    def finish(self):
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
        if response == True:
            self.set_configured(True)
        dlg.destroy()

    def set_configuration(self, config):
        self.enabledTags = []
        for tag in config.get("tags", []):
            self.enabledTags.append(str(tag))

        self.set_configured(True)
            
    def get_configuration(self):
        return {"tags": self.enabledTags}

    def is_configured (self):
        return len(self.enabledTags) > 0

    def get_UID(self):
        return Utils.get_user_string()

class FSpotFactory (DataProvider.DataProviderFactory):
    """
    This class handles the availability of fspot.  If it's not running at startup
    it will listen to dbus until the photo remote control is created.  If that happens
    the FSpot dataprovider pops.  Same way it will go down again when fspot goes
    down
    """
    fspot_key = None

    def __init__ (self, **kwargs):
        DataProvider.DataProviderFactory.__init__(self, **kwargs)

        # connect to singals
        bus = dbus.SessionBus()
        bus.add_signal_receiver(self.handle_photoremote_up, dbus_interface=PHOTOREMOTE_IFACE, signal_name="RemoteUp")
        bus.add_signal_receiver(self.handle_photoremote_down, dbus_interface=PHOTOREMOTE_IFACE, signal_name="RemoteDown")

        # apparently we can't create dataproviders at init time yet,
        # so wait a bit to check for fspot
        gobject.timeout_add(2000, self._check_for_fspot)

    def _check_for_fspot(self):
        if _get_photoremote():
            self.handle_photoremote_up()

    def handle_photoremote_up(self):
        if self.fspot_key:
            return

        self.fspot_key = self.emit_added (
                                klass = FSpotDbusTwoWay,
                                initargs=(),
                                category=conduit.dataproviders.CATEGORY_PHOTOS)

    def handle_photoremote_down(self):
        if not self.fspot_key:
            return

        self.emit_removed(self.fspot_key)
        self.fspot_key = None

