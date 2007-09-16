"""
Draws the applications main window

Also manages the callbacks from menu and GUI items

Copyright: John Stowers, 2006
License: GPLv2
"""
import gobject
import gtk
import gtk.glade
import gnome.ui
import os.path
from gettext import gettext as _

import conduit
from conduit import log,logd,logw
from conduit.Canvas import Canvas
from conduit.Synchronization import SyncManager
from conduit.Tree import DataProviderTreeModel, DataProviderTreeView
from conduit.Conflict import ConflictResolver

class MainWindow:
    """
    The main conduit window.
    """
    def __init__(self, conduitApplication, moduleManager, typeConverter):
        """
        Constructs the mainwindow. Throws up a splash screen to cover 
        the most time consuming pieces
        """
        gnome.init(conduit.APPNAME, conduit.APPVERSION, properties={gnome.PARAM_APP_DATADIR:'/usr/share'})
        gnome.ui.authentication_manager_init()        

        self.conduitApplication = conduitApplication

        #add some additional dirs to the icon theme search path so that
        #modules can provider their own icons
        icon_dirs = [
                    conduit.SHARED_DATA_DIR,
                    conduit.SHARED_MODULE_DIR,
                    os.path.join(conduit.SHARED_DATA_DIR,"icons"),
                    os.path.join(conduit.SHARED_MODULE_DIR,"dataproviders"),
                    os.path.join(conduit.USER_DIR, "modules")
                    ]
        for i in icon_dirs:                    
            gtk.icon_theme_get_default().prepend_search_path(i)
            logd("Adding %s to icon theme search path" % (i))

        self.widgets = gtk.glade.XML(conduit.GLADE_FILE, "MainWindow")
        
        dic = { "on_mainwindow_delete" : self.on_window_closed,
                "on_mainwindow_state_event" : self.on_window_state_event,
                "on_synchronize_activate" : self.on_synchronize_all_clicked,      
                "on_quit_activate" : self.on_window_closed,
                "on_clear_canvas_activate" : self.on_clear_canvas,
                "on_preferences_activate" : self.on_conduit_preferences,
                "on_about_activate" : self.on_about_conduit,
                "on_contents_activate" : self.on_help,
                "on_save1_activate" : self.save_settings,
                None : None
                }
         
        self.widgets.signal_autoconnect(dic)

        #type converter and sync manager
        self.type_converter = typeConverter
        self.sync_manager = SyncManager(self.type_converter)
        self.sync_manager.set_twoway_policy({
                "conflict"  :   conduit.settings.get("twoway_policy_conflict"),
                "deleted"   :   conduit.settings.get("twoway_policy_deleted")}
                )
        
        #Initialize the mainWindow
        self.mainWindow = self.widgets.get_widget("MainWindow")
        if conduit.IS_DEVELOPMENT_VERSION:
            self.mainWindow.set_title("%s %s - DEVELOPMENT RELEASE" % (conduit.APPNAME, conduit.APPVERSION))
        else:
            self.mainWindow.set_title(conduit.APPNAME)
        self.mainWindow.set_position(gtk.WIN_POS_CENTER)
        self.mainWindow.set_icon_name("conduit")
        
        #Configure canvas
        self.canvasSW = self.widgets.get_widget("canvasScrolledWindow")
        self.hpane = self.widgets.get_widget("hpaned1")

        #start up the canvas
        self.canvas = Canvas(
                        parentWindow=self.mainWindow,
                        typeConverter=self.type_converter,
                        syncManager=self.sync_manager,
                        dataproviderMenu=gtk.glade.XML(conduit.GLADE_FILE, "DataProviderMenu"),
                        conduitMenu=gtk.glade.XML(conduit.GLADE_FILE, "ConduitMenu")
                        )
        self.canvasSW.add(self.canvas)
        self.canvasSW.show_all()
        self.canvas.connect('drag-drop', self.drop_cb)
        self.canvas.connect("drag-data-received", self.drag_data_received_data)
        
        # Populate the tree model
        self.dataproviderTreeModel = DataProviderTreeModel() 
        dataproviderScrolledWindow = self.widgets.get_widget("scrolledwindow2")
        self.dataproviderTreeView = DataProviderTreeView(self.dataproviderTreeModel)
        dataproviderScrolledWindow.add(self.dataproviderTreeView)
        dataproviderScrolledWindow.show_all()

        #Set up the expander used for resolving sync conflicts
        self.conflictResolver = ConflictResolver(self.widgets)

        #setup the module manager
        self.moduleManager = moduleManager
        self.dataproviderTreeModel.add_dataproviders(self.moduleManager.get_modules_by_type("source"))
        self.dataproviderTreeModel.add_dataproviders(self.moduleManager.get_modules_by_type("sink"))
        self.dataproviderTreeModel.add_dataproviders(self.moduleManager.get_modules_by_type("twoway"))
        self.moduleManager.connect("dataprovider-available", self.on_dataprovider_available)
        self.moduleManager.connect("dataprovider-unavailable", self.on_dataprovider_unavailable)

        #final GUI setup
        self.hpane.set_position(conduit.settings.get("gui_hpane_postion"))
        #print "GUI POSITION - ",conduit.settings.get("gui_window_size")
        self.dataproviderTreeView.expand_all()
        self.window_state = 0

    def on_conduit_added(self, syncset, cond):
        cond.connect("sync-started", self.on_sync_started)
        cond.connect("sync-completed", self.on_sync_completed)
        cond.connect("sync-conflict", self.conflictResolver.on_conflict)

    def on_conduit_removed(self, syncset, cond):
        pass

    def set_model(self, syncSet):
        self.syncSet = syncSet
        self.syncSet.connect("conduit-added", self.on_conduit_added)
        self.syncSet.connect("conduit-removed", self.on_conduit_removed)
        self.canvas.set_sync_set(syncSet)

    def present(self):
        """
        Present the main window. Enjoy your window
        """
        logd("Presenting GUI")
        self.mainWindow.show_all()
        self.mainWindow.present()
        
    def minimize_to_tray(self):
        """
        Iconifies the main window
        """
        logd("Iconifying GUI")
        self.mainWindow.hide()

    def is_visible(self):
        """
        Returns True if mainWindow is visible
        (not minimized or withdrawn)
        """
        hidden = int(self.window_state) & int(gtk.gdk.WINDOW_STATE_WITHDRAWN)
        minimized = int(self.window_state) & int(gtk.gdk.WINDOW_STATE_ICONIFIED)
        return not (hidden or minimized)

    def on_sync_started(self, thread):
        logd("GUI got sync started")

    def on_sync_completed(self, thread, aborted, error, conflict):
        logd("GUI got sync completed")
       
    def on_dataprovider_available(self, loader, dataprovider):
        """
        Adds the new dataprovider to the treeview
        """
        if dataprovider.enabled == True:
            self.dataproviderTreeModel.add_dataprovider(dataprovider)

    def on_dataprovider_unavailable(self, unloader, dataprovider):
        """
        Removes the dataprovider from the treeview and replaces it with pending dataproviders
        """
        self.dataproviderTreeModel.remove_dataprovider(dataprovider)
        
    def on_synchronize_all_clicked(self, widget):
        """
        Synchronize all valid conduits on the canvas
        """
        for conduit in self.syncSet.get_all_conduits():
            if conduit.datasource is not None and len(conduit.datasinks) > 0:
                self.sync_manager.sync_conduit(conduit)
            else:
                log("Conduit must have a datasource and a datasink")        

    def on_clear_canvas(self, widget):
        """
        Clear the canvas and start a new sync set
        """
        self.canvas.clear_canvas()
    
    def on_conduit_preferences(self, widget):
        """
        Show the properties of the current sync set (status, conflicts, etc
        Edit the sync specific properties
        """
        def restore_policy_state(policy, ask_rb, replace_rb, skip_rb):
            pref = conduit.settings.get("twoway_policy_%s" % policy)
            if pref == "skip":
                skip_rb.set_active(True)
            elif pref == "replace":
                replace_rb.set_active(True)
            else:
                ask_rb.set_active(True)

        def save_policy_state(policy, ask_rb, replace_rb, skip_rb):
            if skip_rb.get_active() == True:
                i = "skip"
            elif replace_rb.get_active() == True:
                i = "replace"
            else:            
                i = "ask"
            conduit.settings.set("twoway_policy_%s" % policy, i)
            return i

        def on_clear_button_clicked(sender, textview):
            conduit.mappingDB.delete()
            textview.get_buffer().set_text(conduit.mappingDB.debug())

        #Build some liststores to display
        convertables = self.type_converter.get_convertables_descriptive_list()
        converterListStore = gtk.ListStore( str )
        for i in convertables:
            converterListStore.append( [i] )
        dataProviderListStore = gtk.ListStore( str, bool )
        for i in self.moduleManager.get_modules_by_type("sink"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.get_input_type(), i.get_output_type()), i.enabled))
        for i in self.moduleManager.get_modules_by_type("source"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.get_input_type(), i.get_output_type()), i.enabled))
        for i in self.moduleManager.get_modules_by_type("twoway"):
            dataProviderListStore.append(("Name: %s\nDescription: %s\n(type:%s in:%s out:%s)" % (i.name, i.description, i.module_type, i.get_input_type(), i.get_output_type()), i.enabled))

        #construct the dialog
        tree = gtk.glade.XML(conduit.GLADE_FILE, "PreferencesDialog")
        #Show the DB contents to help debugging
        if conduit.IS_DEVELOPMENT_VERSION:
            notebook = tree.get_widget("prop_notebook")

            #Show a text window and a button in a VBox
            vbox = gtk.VBox(False,5)

            textView = gtk.TextView()
            textView.set_editable(False)
            textView.get_buffer().set_text(conduit.mappingDB.debug())
            sw = gtk.ScrolledWindow()
            sw.add(textView)
            vbox.pack_start(sw,True,True)

            clear = gtk.Button(None,gtk.STOCK_CLEAR)
            clear.connect("clicked", on_clear_button_clicked, textView)
            vbox.pack_start(clear, False, False)

            notebook.append_page(vbox,gtk.Label('Mapping DB'))
            notebook.show_all()
        
        converterTreeView = tree.get_widget("dataConversionsTreeView")
        converterTreeView.set_model(converterListStore)
        converterTreeView.append_column(gtk.TreeViewColumn('Conversions Available', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )
        dataproviderTreeView = tree.get_widget("dataProvidersTreeView")
        dataproviderTreeView.set_model(dataProviderListStore)
        dataproviderTreeView.append_column(gtk.TreeViewColumn('Name', 
                                        gtk.CellRendererText(), 
                                        text=0)
                                        )                                                   
        dataproviderTreeView.append_column(gtk.TreeViewColumn('Enabled', 
                                        gtk.CellRendererToggle(), 
                                        active=1)
                                        )                                        
                                        
        #fill out the configuration tab
        removable_devices_check = tree.get_widget("removable_devices_check")
        removable_devices_check.set_active(conduit.settings.get("enable_removable_devices"))
        save_settings_check = tree.get_widget("save_settings_check")
        save_settings_check.set_active(conduit.settings.get("save_on_exit"))
        status_icon_check = tree.get_widget("status_icon_check")
        status_icon_check.set_active(conduit.settings.get("show_status_icon")) 
        minimize_to_tray_check = tree.get_widget("minimize_to_tray_check")
        minimize_to_tray_check.set_active(conduit.settings.get("gui_minimize_to_tray")) 

        #get the radiobuttons where the user sets their policy
        conflict_ask_rb = tree.get_widget("conflict_ask_rb")
        conflict_replace_rb = tree.get_widget("conflict_replace_rb")
        conflict_skip_rb = tree.get_widget("conflict_skip_rb")
        deleted_ask_rb = tree.get_widget("deleted_ask_rb")
        deleted_replace_rb = tree.get_widget("deleted_replace_rb")
        deleted_skip_rb = tree.get_widget("deleted_skip_rb")
        #set initial conditions        
        restore_policy_state("conflict", conflict_ask_rb, conflict_replace_rb, conflict_skip_rb)
        restore_policy_state("deleted", deleted_ask_rb, deleted_replace_rb, deleted_skip_rb)
                                        
        #Show the dialog
        dialog = tree.get_widget("PreferencesDialog")
        dialog.set_transient_for(self.mainWindow)
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            conduit.settings.set("save_on_exit", save_settings_check.get_active())
            conduit.settings.set("show_status_icon", status_icon_check.get_active())
            conduit.settings.set("gui_minimize_to_tray", minimize_to_tray_check.get_active())
            policy = {}
            policy["conflict"] = save_policy_state("conflict", conflict_ask_rb, conflict_replace_rb, conflict_skip_rb)
            policy["deleted"] = save_policy_state("deleted", deleted_ask_rb, deleted_replace_rb, deleted_skip_rb)
            self.sync_manager.set_twoway_policy(policy)
        dialog.destroy()                


    def on_about_conduit(self, widget):
        """
        Display about dialog
        """
        dialog = AboutDialog()
        dialog.set_transient_for(self.mainWindow)
        dialog.run()
        dialog.destroy()

    def on_help(self, widget):
        """
        Display help
        """
        gnome.help_display(conduit.APPNAME, None)

    def on_window_state_event(self, widget, event):
        self.window_state = event.new_window_state
        if event.new_window_state == gtk.gdk.WINDOW_STATE_ICONIFIED:
            if conduit.settings.get("gui_minimize_to_tray"):
                self.minimize_to_tray()

    def on_window_closed(self, widget, event=None):
        """
        Check if there are any synchronizations currently in progress and
        ask the user if they wish to cancel them
        """
        busy = False
        quit = False
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
            #FIXME: I want to do this call over DBus but this hangs. Why?
            #sessionBus = dbus.SessionBus()
            #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
            #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
            #conduitApp.Quit()
            self.conduitApplication.Quit()
        
        
    def drop_cb(self, wid, context, x, y, time):
        """
        drop cb
        """
        #print "DND DROP = ", context.targets
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
        
    def save_settings(self, widget):
        """
        Saves the application settings to an XML document.
        Saves the GUI settings (window state, position, etc to gconf)
        """
        #save the canvas
        self.syncSet.save_to_xml()

        #GUI settings
        #print "EXPANDED ROWS - ", self.dataproviderTreeView.get_expanded_rows()
        conduit.settings.set("gui_hpane_postion", self.hpane.get_position())
        conduit.settings.set("gui_window_size", self.mainWindow.get_size())

class SplashScreen:
    """
    Simple splash screen class which shows an image for a predetermined period
    of time or until L{SplashScreen.destroy} is called.
    
    Code adapted from banshee
    """
    DELAY = 1500 #msec
    def __init__(self):        
        """
        Constructor
        """
        #If false the main window should call destroy() to remove the splash
        self.destroyed = True
        
    def show(self):
        """
        Builds the splashscreen and connects the splash window to be destroyed 
        via a timeout callback in L{SplashScreen.DELAY}msec time.

        The splash can also be destroyed manually by the application
        """
        self.wSplash = gtk.Window(gtk.WINDOW_POPUP)
        self.wSplash.set_decorated(False)
        wSplashScreen = gtk.Image()
        wSplashScreen.set_from_file(os.path.join(conduit.SHARED_DATA_DIR,"conduit-splash.png"))

        # Make a pretty frame
        wSplashFrame = gtk.Frame()
        wSplashFrame.set_shadow_type(gtk.SHADOW_OUT)
        wSplashFrame.add(wSplashScreen)
        self.wSplash.add(wSplashFrame)

        # OK throw up the splashscreen
        self.wSplash.set_position(gtk.WIN_POS_CENTER)
        
        #The splash screen is destroyed automatically (via timeout)
        #or when the application is finished loading
        self.destroyed = False

        self.wSplash.show_all()
        # ensure it is rendered immediately
        while gtk.events_pending():
            gtk.main_iteration() 
        # The idle timeout handler to destroy the splashscreen
        gobject.timeout_add(SplashScreen.DELAY,self.destroy)

    def destroy(self):
        """
        Destroys the splashscreen. Can be safely called manually (prior to) 
        or via the timer callback
        """
        if not self.destroyed:
            self.wSplash.destroy()
            self.destroyed = True

class AboutDialog(gtk.AboutDialog):
    def __init__(self):
        gtk.AboutDialog.__init__(self)
        self.set_name(conduit.APPNAME)
        self.set_version(conduit.APPVERSION)
        self.set_comments("Synchronisation for GNOME")
        self.set_website("http://www.conduit-project.org")
        self.set_authors(["John Stowers", "John Carr"])
        self.set_logo_icon_name("conduit")

class StatusIcon(gtk.StatusIcon):
    def __init__(self, conduitApplication):
        gtk.StatusIcon.__init__(self)

        #we need some custom icons
        gtk.icon_theme_get_default().prepend_search_path(conduit.SHARED_DATA_DIR)

        self.conduitApplication = conduitApplication
        menu = '''
            <ui>
             <menubar name="Menubar">
              <menu action="Menu">
               <menuitem action="Sync"/>
               <menuitem action="Quit"/>
               <separator/>
               <menuitem action="About"/>
              </menu>
             </menubar>
            </ui>
        '''
        actions = [
            ('Menu',  None, 'Menu'),
            ('Sync', gtk.STOCK_EXECUTE, '_Synchronize', None, 'Synchronize all dataproviders', self.on_synchronize),
            ('Quit', gtk.STOCK_QUIT, '_Quit', None, 'Close Conduit', self.on_quit),
            ('About', gtk.STOCK_ABOUT, '_About', None, 'About Conduit', self.on_about)]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent        
        self.connect('popup-menu', self.on_popup_menu)
        self.connect('activate', self.on_click)

        #start with the application icon
        self._reset_states()
        self._go_to_idle_state()
        self.set_tooltip("Conduit")
        self.set_visible(True)

    def _reset_states(self):
        self.running = 0
        self.conflict = False
        self.animated_idx = 0
        self.animated_icons = range(1,8)

    def _go_to_idle_state(self):
        self.set_from_icon_name("conduit")
        self.set_tooltip("Synchronization Complete")

    def _go_to_conflict_state(self):
        self.set_from_icon_name("dialog-error")
        self.set_tooltip("Synchronization Error")

    def _go_to_running_state(self):
        self.set_tooltip("Synchronizing")
        if self.animated_idx == self.animated_icons[-1]:
            self.animated_idx = 1
        else:
            self.animated_idx += 1
        self.set_from_icon_name("conduit-progress-%d" % self.animated_idx)
        if self.running == 0:
            if self.conflict:
                self._go_to_conflict_state()
                self._reset_states()
            else:
                self._go_to_idle_state()
                self._reset_states()

            return False
        else:
            return True

    def on_conduit_added(self, syncset, cond):
        cond.connect("sync-started", self._on_sync_started)
        cond.connect("sync-completed", self._on_sync_completed)
        cond.connect("sync-conflict", self._on_sync_conflict)
        #cond.connect("sync-progress", self._on_sync_progress)

    def on_conduit_removed(self, syncset, cond):
        pass

    def _on_sync_started(self, cond):
        self.running += 1
        gobject.timeout_add(100, self._go_to_running_state)
        logd("Icon got sync started")

    def _on_sync_completed(self, cond, aborted, error, conflict):
        self.running -= 1
        logd("Icon got sync completed %s (error: %s)" % (self.running, error))

    def _on_sync_conflict(self, cond, conflict):
        self.conflict = True
        logd("Icon got sync conflict")

    def on_synchronize(self, data):
        #sessionBus = dbus.SessionBus()
        #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
        #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
        #conduitApp.Synchronize()
        self.conduitApplication.Synchronize()

    def on_popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def on_quit(self, data):
        #sessionBus = dbus.SessionBus()
        #obj = sessionBus.get_object(conduit.DBUS_IFACE, "/activate")
        #conduitApp = dbus.Interface(obj, conduit.DBUS_IFACE)
        #conduitApp.Quit()
        self.conduitApplication.Quit()

    def on_about(self, data):
        dialog = AboutDialog()
        dialog.run()
        dialog.destroy()
        
    def on_click(self, status):
        if self.conduitApplication.HasGUI():
            if self.conduitApplication.gui.is_visible():
                self.conduitApplication.gui.minimize_to_tray()
            else:
                self.conduitApplication.gui.present()

def main_loop():
    gtk.main()

def main_quit():
    gtk.main_quit()

