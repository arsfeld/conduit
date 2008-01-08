#!/usr/bin/env python2.5
import gobject
import gtk
import hildon
import os
import logging
log = logging.getLogger("hildonui.UI")

import conduit
from conduit.hildonui.List import DataProviderBox

# FIXME: we probably should share some code between these two
from conduit.hildonui.Canvas import Canvas

from gettext import gettext as _

class MainWindow(hildon.Program):
    def __init__(self, conduitApplication, moduleManager, typeConverter, syncManager):
        hildon.Program.__init__(self)

        #add some additional dirs to the icon theme search path so that
        #modules can provider their own icons
        icon_dirs = [
                    conduit.SHARED_DATA_DIR,
                    conduit.SHARED_MODULE_DIR,
                    os.path.join(conduit.SHARED_DATA_DIR,"icons"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
        for i in icon_dirs:                    
            gtk.icon_theme_get_default().prepend_search_path(i)
            log.debug("Adding %s to icon theme search path" % (i))

        self.conduitApplication = conduitApplication
        self.moduleManager = moduleManager
        self.type_converter = typeConverter
        self.sync_manager = syncManager
        self.sync_manager.set_twoway_policy({
                "conflict"  :   conduit.GLOBALS.settings.get("twoway_policy_conflict"),
                "deleted"   :   conduit.GLOBALS.settings.get("twoway_policy_deleted")}
                )
        self.syncSet = None

        self.mainWindow = hildon.Window()
        self.mainWindow.set_icon_name("conduit")
        # self.mainWindow.resize (800, 480)

        self.mainWindow.connect("destroy", self.on_window_destroyed)
        self.add_window(self.mainWindow)

        self.provider_box = DataProviderBox ()
        self.provider_box.add_dataproviders(self.moduleManager.get_modules_by_type("source"))
        self.provider_box.add_dataproviders(self.moduleManager.get_modules_by_type("sink"))
        self.provider_box.add_dataproviders(self.moduleManager.get_modules_by_type("twoway"))
        self.provider_box.combo.set_active (0)
        self.moduleManager.connect("dataprovider-available", self.on_dataprovider_available)
        self.moduleManager.connect("dataprovider-unavailable", self.on_dataprovider_unavailable)

        # FIXME: we should do something hildon specific
        self.canvas = Canvas(
                        parentWindow=self.mainWindow,
                        typeConverter=self.type_converter,
                        syncManager=self.sync_manager)

        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)

        main_pane = gtk.HPaned ()
        main_pane.add1(self.provider_box)
        main_pane.add2(self.canvas)
        self.mainWindow.add(main_pane)
        gobject.set_application_name(conduit.APPNAME)

    def set_model(self, syncSet):
        self.syncSet = syncSet
        self.toolbar = ConduitToolbar(self.syncSet, self.canvas)
        self.canvas.set_sync_set(syncSet)
        
        self.set_common_toolbar(self.toolbar)

    def present(self):
        """
        Present the main window. Enjoy your window
        """
        self.mainWindow.show_all ()

    def minimize_to_tray(self):
        """
        Iconifies the main window
        """
        log.debug("Iconifying GUI")
        self.mainWindow.hide()

    def is_visible(self):
        """
        Dummy for now
        """
        return True

    def drop_cb(self, wid, context, x, y, time):
        """
        drop cb
        """
        self.canvas.drag_get_data(context, context.targets[0], time)
        return True
        
    def drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
        """
        DND
        """
        dataproviderKey = selection.data
        #FIXME: DnD should be cancelled in the Treeview on the drag-begin 
        #signal and NOT here
        if dataproviderKey != "":
            #Add a new instance if the dataprovider to the canvas.
            new = self.moduleManager.get_new_module_instance(dataproviderKey)
            self.canvas.add_dataprovider_to_canvas(dataproviderKey, new, x, y)
        
        context.finish(True, True, etime)
        return
 
    def on_window_destroyed(self, widget, event=None):
        """
        Check if there are any synchronizations currently in progress and
        ask the user if they wish to cancel them
        """
        busy = False
        quit = False

        if self.syncSet:
            for c in self.syncSet.get_all_conduits(): 
                if c.is_busy():
                    busy = True
               
        if busy:       
            dialog = gtk.MessageDialog(
                            self.mainWindow,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            gtk.MESSAGE_QUESTION,
                            gtk.BUTTONS_YES_NO,_("Synchronization in progress. Do you want to cancel it?")
                            )
            response = dialog.run()
            if response == gtk.RESPONSE_YES:
                quit = True
            else:
                #Dont exit
                dialog.destroy()
                return True
        else:
            quit = True
            
        #OK, if we have decided to quit then call quit on the 
        #DBus interface which will tidy up any pending running
        #non gui tasks
        if quit:
            log.debug("Quitting...")
            #FIXME: I want to do this call over DBus but this hangs. Why?
            #sessionBus = dbus.SessionBus()
            #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
            #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
            #conduitApp.Quit()
            self.conduitApplication.Quit()

    def on_dataprovider_available(self, loader, dataprovider):
        if dataprovider.enabled:
            self.provider_box.add_dataprovider (dataprovider)

    def on_dataprovider_unavailable (self, loader, dataprovider):
        self.provider_box.remove_dataprovider (dataprovider)

class ConduitToolbar(gtk.Toolbar):
    def __init__(self, syncSet, canvas):
        gtk.Toolbar.__init__(self)

        self.syncSet = syncSet

        # canvas
        self.canvas = canvas
        self.canvas.connect("position-changed", self.on_position_changed)

        # remove conduit button 
        self.remove_button = gtk.ToolButton(gtk.STOCK_REMOVE)
        self.remove_button.connect("clicked", self.on_remove)

        # save settings button
        self.save_button = gtk.ToolButton(gtk.STOCK_SAVE)
        self.save_button.connect("clicked", self.on_settings_save)

        # sync all button
        image_widget = gtk.image_new_from_icon_name("conduit", 24)
        self.sync_button = gtk.ToolButton(icon_widget=image_widget)
        self.sync_button.connect("clicked", self.on_sync_all)

        # moving
        self.previous_button = gtk.ToolButton(gtk.STOCK_GO_BACK)
        self.previous_button.connect("clicked", self.on_previous)

        self.label = gtk.Label("0/0")

        self.next_button = gtk.ToolButton(gtk.STOCK_GO_FORWARD)
        self.next_button.connect("clicked", self.on_next)

        # add all items
        self.add_item (self.remove_button)
        self.add_item (gtk.SeparatorToolItem())
        self.add_item (self.previous_button)
        self.add_item (self._create_toolitem(self.label))
        self.add_item (self.next_button)
        self.add_item (gtk.SeparatorToolItem())
        self.add_item (self.sync_button)
        self.add_item (self.save_button)

        self.show_all () 

    def add_item(self, item):
        self.insert (item, -1)       

    def on_remove (self, button):
        current = self.canvas.selectedConduitItem.model
        if not current:
            return

        self.syncSet.remove_conduit(current)

    def on_settings_save (self, button):
        self.syncSet.save_to_xml()

    def on_sync_all (self, button):
        self.canvas.sync_all()

    def on_previous (self, button):
        self.canvas.move_previous()

    def on_next (self, button):
        self.canvas.move_next()

    def on_position_changed(self, canvas):
        self.label.set_text (canvas.get_position_str())

    def _create_toolitem (self, widget):
        toolitem = gtk.ToolItem()
        toolitem.add (widget)

        return toolitem

class SplashScreen:
    def __init__(self):
        pass    

    def show(self):
        pass

    def destroy(self):
        pass

class StatusIcon:
    def __init__(self, conduitApplication):
        pass

    def on_conduit_added(self, syncset, cond):
        pass 

    def on_conduit_removed(self, syncset, cond):
        pass

    def on_click(self, status):
        if self.conduitApplication.HasGUI():
            if self.conduitApplication.gui.is_visible():
                self.conduitApplication.gui.minimize_to_tray()
            else:
                self.conduitApplication.gui.present()
        else:
            self.conduitApplication.BuildGUI()
            self.conduitApplication.ShowGUI()

