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
import gtk, gtk.glade

import nautilus
import dbus, dbus.glib

# we only operate on directories
SUPPORTED_FORMAT = 'x-directory/normal'

#dbus interfaces
APPLICATION_DBUS_IFACE='org.conduit.Application'
DATAPROVIDER_DBUS_IFACE="org.conduit.DataProvider"
CONDUIT_DBUS_IFACE="org.conduit.Conduit"

# supported sinks
FLICKR_TWOWAY="FlickrTwoWay"
PICASA_TWOWAY="PicasaTwoWay"
BOXDOTNET_TWOWAY="BoxDotNetTwoWay"

# source dataprovider
FOLDER_TWOWAY="FolderTwoWay"

# configuration stuff
FOLDER_TWOWAY_CONFIG ="<configuration><folder type='string'>%s</folder><folderGroupName type='string'>Home</folderGroupName><includeHidden type='bool'>False</includeHidden></configuration>"
CONFIG_PATH='~/.conduit/nautilus-extension'

class ItemCallbackHandler:
    """
    This class can be used to create a callback method
    for a given conduit sink
    """
    def __init__ (self, app, sink_name):
        self.app = app
        self.sink_name = sink_name

    def activate_cb(self, menu, folder):
        """
        This is the callback method that can be attached to the
        activate signal of a nautilus menu
        """
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
        sink = bus.get_object(DATAPROVIDER_DBUS_IFACE, sink_path)

        # now create conduit
        conduit_path = self.app.BuildConduit (folder_twoway_path, sink_path)
        conduit = bus.get_object(CONDUIT_DBUS_IFACE, conduit_path)

        # check if we have configuration on disk; set it on dataprovider
        xml = self.get_configuration(self.sink_name)

        if xml:
            sink.SetConfigurationXml(xml)

        # configure the sink
        conduit.ConfigureDataprovider(sink_path)

        # get out configuration xml
        xml = sink.GetConfigurationXml()

        # write it to disk
        self.save_configuration(self.sink_name, xml)

        # do it to me, baby, real good!
        conduit.Sync()

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

class ConduitExtension(nautilus.MenuProvider):
    """
    This is the actual extension
    """
    app = None

    def __init__(self):
        bus = dbus.SessionBus()

        try:
            remote_object = bus.get_object(APPLICATION_DBUS_IFACE,"/")
            self.app = dbus.Interface(remote_object, APPLICATION_DBUS_IFACE)
        except dbus.exceptions.DBusException:
            print "Conduit unavailable"

    def get_file_items(self, window, files):
        # no conduit
        if not self.app:
            return

        # more than one selected?
        if len(files) != 1:
            return

        file = files[0]

        # must be a folder
        if not file.get_mime_type () == SUPPORTED_FORMAT:
            return

        # and we like local, although this might not be necessary
        if file.get_uri_scheme() != 'file':
            return

        # add the flickr item
        flickr_item = nautilus.MenuItem('Conduit::synchronizeToFlickr',
                                        'Synchronize to Flickr',
                                        'Synchronize folder with Flickr')

        cb = ItemCallbackHandler(self.app, FLICKR_TWOWAY)
        flickr_item.connect('activate', cb.activate_cb, file)

        # add picasa
        picasa_item = nautilus.MenuItem('Conduit::synchronizeToPicasa',
                                        'Synchronize to Picasa',
                                        'Synchronize folder with Picasa')

        cb = ItemCallbackHandler(self.app, PICASA_TWOWAY)
        picasa_item.connect('activate', cb.activate_cb, file)

        # add box.net
        box_item = nautilus.MenuItem('Conduit::synchronizeToBoxNet',
                                     'Synchronize to Box.net',
                                     'Synchronize folder with Box.net')

        cb = ItemCallbackHandler(self.app, BOXDOTNET_TWOWAY)
        box_item.connect('activate', cb.activate_cb, file)

        # return all items
        return flickr_item, picasa_item, box_item
       
