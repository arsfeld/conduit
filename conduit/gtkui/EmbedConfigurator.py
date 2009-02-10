import os.path
import gobject
import gtk, gtk.glade
import logging
log = logging.getLogger("gtkui.Config")

from gettext import gettext as _ 
import conduit

class EmbedConfigurator(gobject.GObject):
    '''
    A embed configurator.
    '''

    def __init__(self, window):
        gobject.GObject.__init__(self)
        
        self.window = window
        
        self.showing = False
        self.configs = []
        
        self.vbox = gtk.VBox(spacing = 8)
        self.vbox.set_border_width(6)
        self.vbox.hide()
        
        self.widget = self.vbox
        
        #self.widget = gtk.ScrolledWindow()
        #self.widget.add_with_viewport(self.vbox)
        #self.widget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        
        self.buttons = gtk.HButtonBox()
        self.buttons.set_layout(gtk.BUTTONBOX_END)
        #self.widget.pack_end(self.buttons)
        #self.widget.pack_end(gtk.HSeparator())
        
        self.button_apply = gtk.Button(stock = gtk.STOCK_APPLY)
        self.button_apply.connect("clicked", self._on_apply_clicked)
        self.button_cancel = gtk.Button(stock = gtk.STOCK_CANCEL)
        self.button_cancel.connect("clicked", self._on_cancel_clicked)
        
        self.buttons.pack_start(self.button_cancel)
        self.buttons.pack_start(self.button_apply)

    def _config_changed_cb(self, config, item):
        self._update_modified()
    
    def _update_modified(self):
        modified = True
        for config in self.configs:
            modified = config.is_modified()
            if modified:
                break
        self.button_cancel.set_sensitive(modified)
        self.button_apply.set_sensitive(modified)
        
    def _on_apply_clicked(self, button):
        for config in self.configs:
            if config:
                config.apply_config()
        self._update_modified()
        
    def _on_cancel_clicked(self, button):
        for config in self.configs:
            if config:
                config.cancel_config()
        self._update_modified()
        
    def has_configure_menu(self):
        return False
        
    def run(self):
        return None
        
    def set_controllers(self, config_controllers):
        self.vbox.hide()
        self.vbox.foreach(lambda widget: self.vbox.remove(widget))
        for config in self.configs:
            if config:
                config.cancel_config()
                #self.widget.remove(config.get_config_widget())
                config.hide()        
        self.vbox.pack_end(self.buttons, False, False)        
        #self.widget.show()
        self.configs = config_controllers
        for config in self.configs:
            if config:
                vbox = gtk.HBox(spacing = 8)
                name, icon = config.get_name(), config.get_icon()
                if icon:
                    vbox.pack_start(gtk.image_new_from_pixbuf(icon), False, False)
                if name:
                    lbl = gtk.Label(name)                
                    vbox.pack_start(lbl, False, False)
                if name or icon:
                    self.vbox.pack_start(vbox, False, False)
                self.vbox.pack_start(config.get_config_widget(), False, False)
                self.vbox.pack_start(gtk.HSeparator(), False, False)
                config.show()
                config.connect("changed", self._config_changed_cb)
        self.vbox.show_all()
        self._update_modified()
        
    def get_window(self):
        return self.window
        
    def get_widget(self):
        #for config in self.configs:
        #    config.show()
        return self.widget        
