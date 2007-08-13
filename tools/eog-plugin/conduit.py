import os

import eog
import gtk, gtk.glade

class ExamplePyPlugin(eog.Plugin):
    def __init__(self):
        print "INIT"

    def activate(self, window):
        print "ACTIVATE"

    def deactivate(self, window):
        print "DEACTIVATE"

    def update_ui(self, window):
        print "UPDATE"

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        path = os.path.join(__file__, "..", "config.glade")
        path = os.path.abspath(path)
        xml = gtk.glade.XML(path, "ConfigDialog")

        #get widget refs
        self.dlg = xml.get_widget("ConfigDialog")

        return self.dlg
