"""
Conduit Nautilus extension

Copyright (c) 2007 Thomas Van Machelen <thomas dot vanmachelen at gmail dot com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. The name of the author may not be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import nautilus
import dbus, dbus.glib

try:
    import libconduit
except ImportError:
    import conduit.libconduit as libconduit

DEBUG = True
FOLDER_TWOWAY = "FolderTwoWay"
FOLDER_TWOWAY_CONFIG = "<configuration><folder type='string'>%s</folder><folderGroupName type='string'>Home</folderGroupName><includeHidden type='bool'>False</includeHidden></configuration>"
CONFIG_PATH = '~/.conduit/nautilus-extension'
SUPPORTED_SINKS = {
    "FlickrTwoWay"      :   "Upload to Flickr",
    "PicasaTwoWay"      :   "Upload to Picasa",
    "SmugMugTwoWay"     :   "Upload to SmugMug",
    "BoxDotNetTwoWay"   :   "Upload to Box.net",
    "FolderTwoWay"      :   "Synchronize with Another Folder"
}
if DEBUG:
    SUPPORTED_SINKS["TestFileSink"] = "Test"

class ItemCallbackHandler:
    """
    This class can be used to create a callback method
    for a given conduit sink
    """
    def __init__ (self, sink_name, conduitApplication):
        self.sink_name = sink_name
        self.conduitApp = conduitApplication
        self.conduit = None

    def activate_cb(self, menu, folder):
        """
        This is the callback method that can be attached to the
        activate signal of a nautilus menu
        """
        if self.conduitApp.connected():
            app = self.conduitApp.get_application()
        else:
            return

        # it has got to be there
        if folder.is_gone ():
            return
        
        # get uri
        uri = folder.get_uri()
        
        # check if they needed providers are available
        dps = self.conduitApp.get_dataproviders()

        if not FOLDER_TWOWAY in dps and not self.sink_name in dps:
            return

        # create dataproviders
        folder_twoway_path = app.GetDataProvider(dps[FOLDER_TWOWAY])
        sink_path = app.GetDataProvider(dps[self.sink_name])

        bus = dbus.SessionBus()

        # set up folder config
        folder_twoway = bus.get_object(libconduit.DATAPROVIDER_DBUS_IFACE, folder_twoway_path)
        folder_twoway.SetConfigurationXml(FOLDER_TWOWAY_CONFIG % uri)
        
        # get flickr dbus object
        self.sink = bus.get_object(libconduit.DATAPROVIDER_DBUS_IFACE, sink_path)
        
        # now create conduit
        conduit_path = app.BuildConduit (folder_twoway_path, sink_path)
        self.conduit = bus.get_object(libconduit.CONDUIT_DBUS_IFACE, conduit_path)
        self.conduit.connect_to_signal("SyncCompleted", self.on_sync_completed, dbus_interface=libconduit.CONDUIT_DBUS_IFACE)

        # check if we have configuration on disk; set it on dataprovider
        xml = self.get_configuration(self.sink_name)

        if xml:
            self.sink.SetConfigurationXml(xml)
            
        #Get the syncset
        self.ss = bus.get_object(libconduit.SYNCSET_DBUS_IFACE, libconduit.SYNCSET_GUI_PATH)
        self.ss.AddConduit(self.conduit, dbus_interface=libconduit.SYNCSET_DBUS_IFACE)

        # configure the sink; and perform the actual synchronisation
        # when the configuration is finished
        self.sink.Configure(reply_handler=self._configure_reply_handler,
                            error_handler=self._configure_error_handler)

    def get_configuration(self, sink_name):
        """
        Gets the latest configuration for a given
        dataprovider
        """
        config_path = os.path.expanduser(CONFIG_PATH)

        if not os.path.exists(os.path.join(config_path, sink_name)):
           return

        f = open(os.path.join(config_path, sink_name), 'r')
        xml = f.read ()
        f.close()

        return xml
           
    def save_configuration(self, sink_name, xml):
        """
        Saves the configuration xml from a given dataprovider again
        """
        config_path = os.path.expanduser(CONFIG_PATH)

        if not os.path.exists(config_path):
           os.mkdir(config_path)

        f = open(os.path.join(config_path, sink_name), 'w')
        f.write(xml)
        f.close()
        
    def on_sync_completed(self, abort, error, conflict):
        self.ss.DeleteConduit(self.conduit, dbus_interface=libconduit.SYNCSET_DBUS_IFACE)
        print "Finished"

    def _configure_reply_handler(self):
        """
        Finish the setup: save existing configuration
        and perform synchronise
        """
        # get out configuration xml
        xml = self.sink.GetConfigurationXml()

        # write it to disk
        self.save_configuration(self.sink_name, xml)

        # do it to me, baby, real good!
        self.conduit.Sync(dbus_interface=libconduit.CONDUIT_DBUS_IFACE)

    def _configure_error_handler(self, error):
        """
        Nothing to do anymore
        """
        pass

class ConduitExtension(nautilus.MenuProvider):
    """
    This is the actual extension
    """
    def __init__(self):
        self.debug = DEBUG
        self.conduit = libconduit.ConduitApplicationWrapper(
                                        conduitWrapperKlass=None,
                                        store=False,
                                        debug=self.debug
                                        )
        self.conduit.connect("conduit-started", self._on_conduit_started)
        self.conduit.connect_to_conduit(startConduit=False)
        self.dps = self._get_dataproviders()

    def _get_dataproviders(self):
        #restrict dps to those we know about
        return [dp for dp in self.conduit.get_dataproviders() if dp in SUPPORTED_SINKS]

    def _on_conduit_started(self, sender, started):
        self.dps = self._get_dataproviders()

    def get_file_items(self, window, files):
        if self.conduit.connected():
            if len(files) == 1:
                file_ = files[0]
                if file_.is_directory():
                    submenu = nautilus.Menu()
                    for dp in self.dps:
                        name = dp
                        desc = SUPPORTED_SINKS[dp]

                        #make the menu item
                        item = nautilus.MenuItem(
                                            'Conduit::SynchronizeTo%s' % name,
                                            desc,
                                            '',
                                            'image-x-generic'
                        )
                        cb = ItemCallbackHandler(name, self.conduit)
                        item.connect('activate', cb.activate_cb, file_)

                        submenu.append_item(item)

                    menuitem = nautilus.MenuItem(
                                            'Conduit::',
                                            'Conduit',
                                            '',
                                            'conduit'
                    )
                    menuitem.set_submenu(submenu)
                    return menuitem,

        return None
       
