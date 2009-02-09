import os.path
import gobject
import gtk, gtk.glade
import logging
log = logging.getLogger("gtkui.WindowConfigurator")

from gettext import gettext as _ 
import conduit
import conduit.gtkui.ConfigContainer as ConfigContainer

class WindowConfigurator(gobject.GObject):
    """
    A window configurator to embed a configuration widget.
    """
    
    CONFIG_WINDOW_TITLE_TEXT = _("Configure")
    
    #Show multiple containers or only shows the currently selected dataprovider
    #This should be set to False until all dataproviders use the new system
    MULTIPLE_VIEW = False
    #Use a notebook instead of stacking the containers. Notebooks are very good
    #for large configuration windows, that end up being larger then the screen
    #height (happens frequently).
    #Creates a border when not used with MULTIPLE_VIEW, so it's disabled while 
    #that is disabled (and should be enabled otherwise)
    NOTEBOOK = MULTIPLE_VIEW
    
    def __init__(self, window):
        """
        @param window: Parent window (this dialog is modal)
        @type window: C{gtk.Window}
        """
        gobject.GObject.__init__(self)
        
        self.showing = False
        self.built_configs = False
        
        #self.dialogParent = window
        #The dialog is loaded from a glade file
        #gladeFile = os.path.join(conduit.SHARED_DATA_DIR, "conduit.glade")
        #widgets = gtk.glade.XML(gladeFile, "DataProviderConfigDialog")

        self.dialog = gtk.Dialog(self.CONFIG_WINDOW_TITLE_TEXT,
                          window,
                          gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                          (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                           gtk.STOCK_OK, gtk.RESPONSE_OK,
                           gtk.STOCK_HELP, gtk.RESPONSE_HELP))
        #TODO: Unless we actually have a help to show, make the help button 
        #disabled.
        #BTW, modules should be able to define their own help
        self.dialog.set_has_separator(False)
        self.dialog.set_response_sensitive(gtk.RESPONSE_HELP, False)
        self.dialog.set_default_size(300, -1)
        #self.dialog = widgets.get_widget("DataProviderConfigDialog")
        #self.dialog.set_transient_for(self.dialogParent)
        #self.dialog.set_title(WindowConfigurator.CONFIG_WINDOW_TITLE_TEXT)
        #self.dialog.set_border_width(6)
        
        #self.configVBox = widgets.get_widget("configVBox")
        self.dialog_box = self.dialog.vbox
        
        self.dialog_box.pack_start(self._make_config_widget())        
        #self.configVBox.pack_start(self.conduit_config.get_config_widget())
        self.dialog_box.show_all()        
        
        self.container_widgets = {}
        
    def _make_config_widget(self):
        if self.NOTEBOOK:
            self.tabs = {}
            self.notebook = gtk.Notebook()
            self.notebook.set_border_width(8)
            self.notebook.set_show_tabs(self.MULTIPLE_VIEW)
            return self.notebook
        else:
            self.containers_box = gtk.VBox(spacing = 8)
            self.containers_box.set_border_width(6)        
            return self.containers_box
        
    def set_containers(self, containers):
        self._clear_containers()
        self.built_containers = False
        
        self.containers = containers
        #self.configVBox.hide()
        #import threading
        #log.debug("THREADS: %s" % threading.activeCount())
        #if self.notebook:
        #    self.configVBox.remove(self.notebook)
        #self.notebook = gtk.Notebook()
        #self.configVBox.pack_start(self.notebook)
        
        #self.notebook.show_all()
        #self.configVBox.pack_start(self.config.get_config_widget())
        
    def _clear_containers(self):
        if self.NOTEBOOK:
            #self.notebook.foreach(lambda widget: self.notebook.remove(widget))
            while self.notebook.get_n_pages() > 0:
                self.notebook.remove_page(0)
            self.tabs = {}
        else:
            #self.containers_box.foreach(lambda widget: self.containers_box.remove(widget))
            for container, widget in self.container_widgets.iteritems():
                self.containers_box.remove(widget)
                container_widget = container.get_config_widget()
                container_widget.get_parent().remove(container_widget)
        self.container_widgets = {}
        
    def _add_container(self, container, container_widget):
        if self.NOTEBOOK:
            hbox = gtk.HBox(spacing = 8)       
            hbox.pack_start(gtk.image_new_from_pixbuf(container.get_icon()), False, False)
            lbl = gtk.Label(container.get_name())
            hbox.pack_start(lbl, False, False, 4)
            hbox.show_all()
            container_widget.set_border_width(8)
            widget = container_widget
            tab_index = self.notebook.append_page(container_widget, hbox)
            self.tabs[container] = tab_index
            self.notebook.show_all()
        else:
            container_box = gtk.VBox(spacing = 8)
            widget = container_box
            if self.MULTIPLE_VIEW:
                title_box = gtk.HBox(spacing = 8)                        
                title_box.pack_start(gtk.image_new_from_pixbuf(container.get_icon()), False, False)
                lbl = gtk.Label(container.get_name())
                title_box.pack_start(lbl, False, False, 4)
                title_box.show_all()
                container_box.pack_start(title_box, False, False)
            #config_widget = config.get_config_widget()
            container_box.pack_start(container_widget, True, True)
            container_box.pack_start(gtk.HSeparator(), False, False)
            self.containers_box.pack_start(container_box)
            self.containers_box.show_all()
        self.container_widgets[container] = widget
    
    def build_containers(self):
        if self.built_containers:
            return
        for index, container in enumerate(self.containers):
            if not container:
                continue
            container_widget = container.get_config_widget()
            #FIXME: The situation below is never reached.
            #The only way to reach it is if the UI allowed a dataprovider to be
            #configured even if it shouldnt. Even then, the canvas filters when
            #there is no configuration container. 
            if not container_widget:
                container_widget = gtk.Label("No configuration needed for this dataprovider")
            self._add_container(container, container_widget)
        self.built_containers = True 
    
    def has_configure_menu(self):
        return True
        
    def get_widget(self):
        return None
        
    def get_window(self):
        return self.dialog
        
    def run(self, config_container):
        """
        Runs the dialog, return True if OK is clicked, False otherwise
        
        @param config_container: container that should be focused, such as the 
            currently selected dataprovider (in a notebook, the currently 
            selected page belongs to this container)
        """
        self.build_containers()
        self.showing = True
        if config_container and not self.MULTIPLE_VIEW:
            assert config_container in self.container_widgets
            for container, container_widget in self.container_widgets.iteritems():
                if container != config_container:
                    #log.debug("Hiding: %s" % container)
                    container_widget.hide()       
                    
            #log.debug("Showing: %s" % config_container)         
            config_container.show()
            self.container_widgets[config_container].show()
            containers = [config_container]
        else:
            for container, container_widget in self.container_widgets.iteritems():
                container_widget.show()
                container.show()
            containers = self.container_widgets.keys()
        if self.NOTEBOOK and config_container:
            self.notebook.set_current_page(self.tabs[config_container])
        #self.dialog.show()
        self.dialog.reshow_with_initial_size()
        resp = self.dialog.run()
        for container in containers:
            container.hide()
        self.dialog.hide()
        #self.dialog = None
        self.showing = False
        if resp == gtk.RESPONSE_OK:
            for container in containers:
                container.apply_config()
        else:
            for container in containers:
                container.cancel_config()
        return (resp == gtk.RESPONSE_OK)
