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
import conduit.dataproviders.Image as Image

from gettext import gettext as _

MODULES = {
	"FSpotDbusTwoWay" :     { "type": "dataprovider"    },
}

NAME_IDX = 0
ID_IDX = 1

class FSpotDbusTwoWay(Image.ImageTwoWay):
    _name_ = _("F-Spot")
    _description_ = _("Synchronize your F-Spot photos")
    _category_ = conduit.dataproviders.CATEGORY_PHOTOS
    _icon_ = "f-spot"
    _configurable_ = True

    SERVICE_PATH = "org.gnome.FSpot"
    PHOTOREMOTE_IFACE = "org.gnome.FSpot.PhotoRemoteControl"
    PHOTOREMOTE_PATH = "/org/gnome/FSpot/PhotoRemoteControl"

    TAGREMOTE_IFACE = "org.gnome.FSpot.TagRemoteControl"
    TAGREMOTE_PATH = "/org/gnome/FSpot/TagRemoteControl"

    def __init__(self, *args):
        Image.ImageTwoWay.__init__(self)

        self.update_configuration(
            tags = ([], self.set_tags, self.get_tags),
        )
        
        self.enabledTags = []
        self.photos = []
        self.has_roll = False
        self.photo_remote = None
        self.tag_remote = None
        
        self._connection_name = None

        self.list_store = None

        self._connect_to_fspot()
        self._hookup_signal_handlers()
        
    def set_tags(self, tags):
        self.enabledTags = []
        for tag in tags:
            self.enabledTags.append(str(tag))

    def get_tags(self):
        return self.enabledTags

    def _connect_to_fspot(self):
        bus = dbus.SessionBus()
        if Utils.dbus_service_available(FSpotDbusTwoWay.SERVICE_PATH, bus):
            #If the connection was broken and remade, the connection name changes
            #and the connection objects no longer works. 
            #F-Spot restarting does exactly that, so we need to remake our objects.
            connection_name = bus.get_name_owner(FSpotDbusTwoWay.SERVICE_PATH)
            if self._connection_name != connection_name:
                self.photo_remote = None
                self.tag_remote = None
            self._connection_name = connection_name
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
        else:
            self.photo_remote = None
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
            raise Exceptions.RefreshError(_("FSpot not available"))
        
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
            raise Exceptions.SyncronizeError (_("F-Spot DBus interface is operating in read-only mode"))

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
            return conduit.datatypes.Rid(uid=str(id))
        except:
            raise Exceptions.SynchronizeError (_('Import Failed'))

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

    def config_setup(self, config):
        RUNNING_MESSAGE = _("F-Spot is running")
        STOPPED_MESSAGE = _("Please start F-Spot or activate the D-Bus Extension")

        def start_fspot(button):
            #would be cleaner if we could autostart using dbus,
            #dbus.SessionBus().start_service_by_name(self.SERVICE_PATH)
            gobject.spawn_async(
                    ("f-spot",), 
                    flags=gobject.SPAWN_SEARCH_PATH|gobject.SPAWN_STDOUT_TO_DEV_NULL|gobject.SPAWN_STDERR_TO_DEV_NULL
            )

        def watch(name):
            connected = bool(name and self._connect_to_fspot())
            start_fspot_config.enabled = not connected
            tags_config.enabled = connected
            if connected:
                tags_config.choices = self._get_all_tags()
            else:
                tags_config.choices = tags_config.value
            add_tags_section.enabled = connected            
            if connected:
                status_label.value = RUNNING_MESSAGE
            else:
                status_label.value = STOPPED_MESSAGE

        status_label = config.add_item(_("Status"), "label")
        start_fspot_config = config.add_item(_("Start F-Spot"), "button",
            initial_value = start_fspot
        )

        config.add_section(_("Tags"))
        tags_config = config.add_item(_("Tags"), "list",
            config_name = 'tags',
            choices = self.enabledTags,
        )

        def add_tag_cb(button):
            text = tag_name_config.get_value()
            newtags = text.split(',')
            for tag in newtags:
                self._create_tag (tag.strip ())   
            tags_config.set_choices(self._get_all_tags())
            tag_name_config.set_value('')

        add_tags_section = config.add_section(_("Add tags"))
        tag_name_config = config.add_item(_("Tag name"), "text",
            initial_value = ""
        )
        config.add_item(_("Add tag"), "button",
            initial_value = add_tag_cb
        )
        dbus.SessionBus().watch_name_owner(self.SERVICE_PATH, watch)

    def get_UID(self):
        return Utils.get_user_string()


