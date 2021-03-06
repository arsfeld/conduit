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

# we only operate on directories
SUPPORTED_FORMAT = 'x-directory/normal'

#dbus interfaces
APPLICATION_DBUS_IFACE='org.conduit.Application'
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"
SYNCSET_DBUS_IFACE="org.conduit.SyncSet"

# supported sinks
SUPPORTED_SINKS = {
    "FlickrTwoWay"      :   "Upload to Flickr",
    "PicasaTwoWay"      :   "Upload to Picasa",
    "SmugMugTwoWay"     :   "Upload to SmugMug",
    "BoxDotNetTwoWay"   :   "Upload to Box.net",
#    "FolderTwoWay"      :   "Synchronize with Another Folder"
}

# source dataprovider
FOLDER_TWOWAY="FolderTwoWay"

# configuration stuff
FOLDER_TWOWAY_CONFIG ="<configuration><folder type='string'>%s</folder><folderGroupName type='string'>Home</folderGroupName><includeHidden type='bool'>False</includeHidden></configuration>"
CONFIG_PATH='~/.conduit/nautilus-extension'

# add to gui or dbus
SYNCSET_PATH = '/syncset/gui'

class ItemCallbackHandler:
    """
    This class can be used to create a callback method
    for a given conduit sink
    """
    def __init__ (self, sink_name, conduitApplication):
        self.sink_name = sink_name
        self.app = conduitApplication
        self.conduit = None

    def activate_cb(self, menu, folder):
        """
        This is the callback method that can be attached to the
        activate signal of a nautilus menu
        """
        if not self.app:
            return

        # it has got to be there
        if folder.is_gone ():
            return
        
        # get uri
        uri = folder.get_uri()
        
        # check if they needed providers are available
        dps = self.app.GetAllDataProviders()

        if not FOLDER_TWOWAY in dps and not self.sink_name in dps:
            return

        # create dataproviders
        folder_twoway_path = self.app.GetDataProvider(FOLDER_TWOWAY)
        sink_path = self.app.GetDataProvider(self.sink_name)

        bus = dbus.SessionBus()

        # set up folder config
        folder_twoway = bus.get_object(DATAPROVIDER_DBUS_IFACE, folder_twoway_path)
        folder_twoway.SetConfigurationXml(FOLDER_TWOWAY_CONFIG % uri)
        
        # get flickr dbus object
        self.sink = bus.get_object(DATAPROVIDER_DBUS_IFACE, sink_path)
        
        # now create conduit
        conduit_path = self.app.BuildConduit (folder_twoway_path, sink_path)
        self.conduit = bus.get_object(CONDUIT_DBUS_IFACE, conduit_path)
        self.conduit.connect_to_signal("SyncCompleted", self.on_sync_completed, dbus_interface=CONDUIT_DBUS_IFACE)

        # check if we have configuration on disk; set it on dataprovider
        xml = self.get_configuration(self.sink_name)

        if xml:
            self.sink.SetConfigurationXml(xml)
            
        #Get the syncset
        self.ss = bus.get_object(SYNCSET_DBUS_IFACE, SYNCSET_PATH)
        self.ss.AddConduit(self.conduit, dbus_interface=SYNCSET_DBUS_IFACE)

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
        self.ss.DeleteConduit(self.conduit, dbus_interface=SYNCSET_DBUS_IFACE)
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
        self.conduit.Sync(dbus_interface=CONDUIT_DBUS_IFACE)

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
        obj = dbus.SessionBus().get_object('org.freedesktop.DBus', '/org/freedesktop/DBus') 
        self.dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus')
        self.dbus_iface.connect_to_signal("NameOwnerChanged", self._on_name_owner_changed)

        self.conduitApp = None
        self.dps = []
        
        #check if conduit is running
        self._on_name_owner_changed(APPLICATION_DBUS_IFACE,'','')
        
    def _get_conduit_app (self):
        bus = dbus.SessionBus()
        try:
            remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
            return dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)
        except dbus.exceptions.DBusException:
            print "COULD NOT CONNECT TO CONDUIT"
            return None

    def _populate_available_dps(self):
        if self.conduitApp != None and self.dps == []:
            for dp in self.conduitApp.GetAllDataProviders():
                if dp in SUPPORTED_SINKS:
                    self.dps.append(dp)

    def _on_name_owner_changed(self, name, oldOwner, newOwner):
        if name == APPLICATION_DBUS_IFACE:
            if self.dbus_iface.NameHasOwner(APPLICATION_DBUS_IFACE):
                self.conduitApp = self._get_conduit_app()
                print "Conduit Started"
            else:
                print "Conduit Stopped"
                self.conduitApp = None
        
    def get_file_items(self, window, files):
        if self.conduitApp == None:
            return

        # more than one selected?
        if len(files) != 1:
            return

        file = files[0]

        # must be a folder
        if not file.get_mime_type () == SUPPORTED_FORMAT:
            return

        # add available items
        self._populate_available_dps()
        items = []
        for dp in self.dps:
            name = dp
            desc = SUPPORTED_SINKS[dp]

            #make the menu item
            item = nautilus.MenuItem(
                                'Conduit::synchronizeTo%s' % name,
                                desc,
                                '',
                                'image-x-generic')

            cb = ItemCallbackHandler(name, self.conduitApp)
            item.connect('activate', cb.activate_cb, file)
            items.append(item)

        # return all items
        return items
       
