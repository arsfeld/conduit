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
                    "InitialValue" : value or function
                    "UserData" : tuple of additional args to callback (optional)
                    }
                ]
                
    Or, alternatively:

        maps = [
                    {
                    "Name" : "Setting Name",
                    "Kind" : "text", "check" or "list",
                    "Callback" : function,
                    "InitialValue" : value or function
                    "Values": list if Kind = "list"
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
        self.customSettings = gtk.Table(rows=0, columns=2)
        self.customSettings.set_row_spacings(4)
        self.customSettings.set_border_width(4)
        
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
            args = w["UserData"]

            #FIXME: This seems hackish
            if isinstance(w["Widget"], gtk.Entry):
                w["Callback"](w["Widget"].get_text(), *args)
            elif isinstance(w["Widget"], gtk.CheckButton):
                w["Callback"](w["Widget"].get_active(), *args)
            elif w["Kind"] == "list":
                w["Callback"](w["Widget"].get_active(), w["Widget"].get_active_text(), *args)
            else:
                # Just return the widget, so the caller should know what to do with this
                w["Callback"](w["Widget"], *args)

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
        return resp == gtk.RESPONSE_OK
        
    def build_child(self):
        """
        For each item in the mappings list create the appropriate widget
        """
        #For each item in the mappings list create the appropriate widget
        for l in self.mappings:
            if "Title" in l:
                label = gtk.Label(l["Title"])
            if 'Kind' in l:
                kind = l['Kind']
                # I'm sure john will hate this
                password = gtk.Entry()
                password.set_visibility( False )
                widget = {'text': gtk.Entry(),
                          'list': gtk.combo_box_new_text(),
                          'check': gtk.CheckButton(),
                          'password': password }[kind]
            elif 'Widget' in l:
                kind = None
                #New instance of the widget
                widget = l["Widget"]()
            else:
                raise Exception("Configuration Kind or Widget not specified")
                
            label_text = l["Name"]
            if label_text[len(label_text) - 1] != ':':
                label_text += ':'
            #gtkEntry has its label beside it
            label = gtk.Label(label_text)
            label.set_alignment(0.0, 0.5)

            if callable(l["InitialValue"]):
                l["InitialValue"](widget)            
            elif kind == 'list':
                index = 0
                for name in l["Values"]:
                    widget.append_text(name)
                    if name == l["InitialValue"]:
                        widget.set_active(index)
                    index += 1                
            #FIXME: I am ashamed about this ugly hackery and dupe code....
            elif isinstance(widget, gtk.Entry):
                widget.set_text(str(l["InitialValue"]))
            elif isinstance(widget, gtk.CheckButton):
                #gtk.CheckButton has its label built in
                label = None
                widget.set_label(l["Name"])
                widget.set_active(bool(l["InitialValue"]))

            if "UserData" in l:
                args = l["UserData"]
            else:
                args = ()
                                       
            #FIXME: There must be a better way to do this but we need some way 
            #to identify the widget *instance* when we save the values from it            
            self.widgetInstances.append({
                                        "Widget" : widget,
                                        "Kind" : kind,
                                        "Callback" : l["Callback"],
                                        "UserData" : args
                                        })
                                        
            table = self.customSettings
            row = table.get_property('n-rows') + 1
            table.resize(row, 2)
            if label:
                table.attach(label, 0, 1, row - 1, row, xpadding = 8)
                table.attach(widget, 1, 2, row - 1, row)
            else:
                table.attach(widget, 0, 2, row - 1, row, xpadding = 8)
