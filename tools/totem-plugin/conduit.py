import os
import totem
import gtk
import dbus, dbus.glib

try:
    import libconduit
except ImportError:
    import conduit.libconduit as libconduit

DEBUG = True
MENU_PATH="/tmw-menubar/movie/properties"
SUPPORTED_SINKS = {
    "YouTubeTwoWay" : "Upload to YouTube",
}
if DEBUG:
    SUPPORTED_SINKS["TestVideoSink"] = "Test"

class TotemConduitWrapper(libconduit.ConduitWrapper):

    CONFIG_NAME="totem-plugin"

    def add_rowref(self):
        #store the rowref in the store with the icon conduit gave us
        info = self.conduit.SinkGetInformation(dbus_interface=libconduit.EXPORTER_DBUS_IFACE)
        desc = SUPPORTED_SINKS[self.name]
        self._add_rowref(
                name=desc,
                uri="",
                status="ready",
                pixbuf=None
        )

class ConduitPlugin(totem.Plugin):
    def __init__(self):
        self.debug = DEBUG
        self.conduit = libconduit.ConduitApplicationWrapper(
                                        conduitWrapperKlass=TotemConduitWrapper,
                                        addToGui=self.debug,
                                        store=True,
                                        debug=self.debug
                                        )
        self.conduit.connect("conduit-started", self._on_conduit_started)
        self.running = self.conduit.connect_to_conduit(startConduit=True)
        self.opened = False

    def _on_conduit_started(self, sender, started):
        self.running = started
        self.top_level_action.set_sensitive(self.opened and self.running)

    def _on_upload_clicked(self, action, totem_object):
        current_uri = totem_object.get_current_mrl()
        name = action.get_property("name")

        # Add the file to the list and sync it immediately
        self.conduit.upload(name, current_uri, None)
        self.conduit.sync()

    def _on_file_opened(self, totem_object, mrl):
        self.opened = True
        self.top_level_action.set_sensitive(self.running)

    def _on_file_closed(self, totem_object):
        self.opened = False
        self.top_level_action.set_sensitive(False)

    def activate(self, totem_object):
        totem_object.connect("file-opened", self._on_file_opened)
        totem_object.connect("file-closed", self._on_file_closed)

        ui_action_group = gtk.ActionGroup("ConduitPluginActions")
        manager = totem_object.get_ui_manager()

        # Make an action for each sink
        for sink_name in SUPPORTED_SINKS:
            desc = SUPPORTED_SINKS[sink_name]
            action = gtk.Action(name = sink_name,
                         stock_id = "internet",
                         label = desc,
                         tooltip = "")
            action.connect("activate", self._on_upload_clicked, totem_object)
            ui_action_group.add_action(action)

        # Create a top-level menu
        self.top_level_action = gtk.Action(name = "sync",
                        stock_id = "internet",
                        label = _("_Share"),
                        tooltip = "")
        ui_action_group.add_action(self.top_level_action)

        manager.insert_action_group(ui_action_group, -1)

        mid = manager.new_merge_id()
        manager.add_ui(merge_id = mid,
                path = MENU_PATH,
                name = "sync",
                action = "sync",
                type = gtk.UI_MANAGER_MENU,
                top = False)

        # Add each action to the menu
        for sink_name in SUPPORTED_SINKS:
            mid = manager.new_merge_id()
            manager.add_ui(merge_id = mid,
                    path = "/tmw-menubar/movie/sync/",
                    name = sink_name, 
                    action = sink_name,
                    type = gtk.UI_MANAGER_MENUITEM, 
                    top = False)

        # Make sure the menu starts disabled
        self.top_level_action.set_sensitive(False)

    def deactivate(self, window):
        pass

    def update_ui(self, window):
        pass

    def is_configurable(self):
        return False
