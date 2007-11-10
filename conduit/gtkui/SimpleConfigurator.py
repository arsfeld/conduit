import os.path
import gtk, gtk.glade
import logging
log = logging.getLogger("gtkui.Config")


import conduit

class SimpleConfigurator:
    """
    Provides a simple modal configuration dialog for dataproviders.
    
    Simply provide a list of dictionarys in the following format::
    
        maps = [
                    {
                    "Name" : "Setting Name",
                    "Widget" : gtk.TextView,
                    "Callback" : function,
                    "InitialValue" : value
                    }
                ]
    """
    
    CONFIG_WINDOW_TITLE_TEXT = "Configure "
    
    def __init__(self, window, dp_name, config_mappings = []):
        """
        @param window: Parent window (this dialog is modal)
        @type window: C{gtk.Window}
        @param dp_name: The dataprovider name to display in the dialog title
        @type dp_name: C{string}
        @param config_mappings: The list of dicts explained earlier
        @type config_mappings: C{[{}]}
        """
        self.mappings = config_mappings
        #need to store ref to widget instances
        self.widgetInstances = []
        self.dialogParent = window
        #the child widget to contain the custom settings
        self.customSettings = gtk.VBox(False, 5)
        
        #The dialog is loaded from a glade file
        gladeFile = os.path.join(conduit.SHARED_DATA_DIR, "conduit.glade")
        widgets = gtk.glade.XML(gladeFile, "DataProviderConfigDialog")
        callbacks = {
                    "on_okbutton_clicked" : self.on_ok_clicked,
                    "on_cancelbutton_clicked" : self.on_cancel_clicked,
                    "on_helpbutton_clicked" : self.on_help_clicked,
                    "on_dialog_close" : self.on_dialog_close
                    }
        widgets.signal_autoconnect(callbacks)
        self.dialog = widgets.get_widget("DataProviderConfigDialog")
        self.dialog.set_transient_for(self.dialogParent)
        self.dialog.set_title(SimpleConfigurator.CONFIG_WINDOW_TITLE_TEXT + dp_name)

        #The contents of the dialog are built from the config mappings list
        self.build_child()
        vbox = widgets.get_widget("configVBox")
        vbox.pack_start(self.customSettings)
        self.customSettings.show_all()        
        
    def on_ok_clicked(self, widget):
        """
        on_ok_clicked
        """
        log.debug("OK Clicked")
        for w in self.widgetInstances:
            #FIXME: This seems hackish
            if isinstance(w["Widget"], gtk.Entry):
                w["Callback"](w["Widget"].get_text())
            elif isinstance(w["Widget"], gtk.CheckButton):
                w["Callback"](w["Widget"].get_active())
            else:
                log.warn("Dont know how to retrieve value from a %s" % w["Widget"])

        self.dialog.destroy()
        
    def on_cancel_clicked(self, widget):
        """
        on_cancel_clicked
        """
        log.debug("Cancel Clicked")
        self.dialog.destroy()
        
    def on_help_clicked(self, widget):
        """
        on_help_clicked
        """
        log.debug("Help Clicked")
        
    def on_dialog_close(self, widget):
        """
        on_dialog_close
        """
        log.debug("Dialog Closed")
        self.dialog.destroy()                       

    def run(self):
        """
        run
        """
        resp = self.dialog.run()
        
    def build_child(self):
        """
        For each item in the mappings list create the appropriate widget
        """
        #For each item in the mappings list create the appropriate widget
        for l in self.mappings:
            #New instance of the widget
            widget = l["Widget"]()
            #all get packed into an HBox
            hbox = gtk.HBox(False, 5)

            #FIXME: I am ashamed about this ugly hackery and dupe code....
            if isinstance(widget, gtk.Entry):
                #gtkEntry has its label beside it
                label = gtk.Label(l["Name"])
                hbox.pack_start(label)
                widget.set_text(str(l["InitialValue"]))
            elif isinstance(widget, gtk.CheckButton):
                #gtk.CheckButton has its label built in
                widget = l["Widget"](l["Name"])
                widget.set_active(bool(l["InitialValue"]))                        
                #FIXME: There must be a better way to do this but we need some way 
                #to identify the widget *instance* when we save the values from it
            self.widgetInstances.append({
                                        "Widget" : widget,
                                        "Callback" : l["Callback"]
                                        })
            #pack them all together
            hbox.pack_start(widget)
            self.customSettings.pack_start(hbox)
