import gtk
import logging
log = logging.getLogger("hildonui.List")

import conduit

class DataProviderBox(gtk.VBox):
    DND_TARGETS = [
        ('conduit/element-name', 0, 0)
    ]
    def __init__(self):
        gtk.VBox.__init__(self)

        # MODEL
        # keep a dict of category - dp list
        self.categories = {}
        self.combo = gtk.combo_box_new_text ()
        self.dp_store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        # populate with dataproviders
        self.add_dataproviders(
            conduit.GLOBALS.moduleManager.get_modules_by_type("source","sink","twoway")
            )
        conduit.GLOBALS.moduleManager.connect("dataprovider-available", self.on_dataprovider_available)
        conduit.GLOBALS.moduleManager.connect("dataprovider-unavailable", self.on_dataprovider_unavailable)

        # VIEW
        # category combo
        self.combo.connect ("changed", self.on_combo_changed)
        self.pack_start(self.combo, False, False)
        # tree view
        self.tree = gtk.TreeView (self.dp_store)
        col = gtk.TreeViewColumn()
        render_pixbuf = gtk.CellRendererPixbuf()
        col.pack_start(render_pixbuf, expand=False)
        col.add_attribute(render_pixbuf, 'pixbuf', 0)
        render_text = gtk.CellRendererText()
        col.pack_start(render_text, expand=True)
        col.add_attribute(render_text, 'text', 1)
        self.tree.append_column (col)

        # Dnd
        self.tree.enable_model_drag_source( gtk.gdk.BUTTON1_MASK,
                                            self.DND_TARGETS,
                                            gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_MOVE)
        self.tree.drag_source_set( gtk.gdk.BUTTON1_MASK | gtk.gdk.BUTTON3_MASK,
                                   self.DND_TARGETS,
                                   gtk.gdk.ACTION_COPY | gtk.gdk.ACTION_LINK)
        #self.connect('drag-begin', self.on_drag_begin)
        self.tree.connect('drag-data-get', self.on_drag_data_get)
        self.tree.connect('drag-data-delete', self.on_drag_data_delete)

        self.pack_start(self.tree, True, True)
        
    def on_dataprovider_available(self, loader, dataprovider):
        if dataprovider.enabled:
            self.add_dataprovider (dataprovider)

    def on_dataprovider_unavailable (self, loader, dataprovider):
        self.remove_dataprovider (dataprovider)

    def add_dataproviders(self, dpw=[]):
        """
        Adds all enabled dataproviders to the model
        """
        #Only display enabled modules
        module_wrapper_list = [m for m in dpw if m.enabled]
        
        #Add them to the module
        for mod in module_wrapper_list:
            self.add_dataprovider(mod)
 
    def add_dataprovider (self, dpw):
        """
        Adds a new dataprovider
        """
        log.debug("Adding dataprovider %s to List" % dpw)

        category_name = dpw.category.name

        if not self.categories.has_key(category_name):
            self.combo.append_text (category_name)
            self.categories[category_name] = [dpw]
        else:
            self.categories[category_name].append (dpw)

        self.reload_category_if_current(category_name)            

    def remove_dataprovider (self, dpw):
        """
        Remove dataprovider
        """
        category_name = dpw.category.name

        if not self.categories.has_key (category_name):
            return

        self.categories[category_name].remove(dpw) 
        self.reload_category_if_current (category_name)

    def on_combo_changed (self, combo):
        """
        Reload the category if the combo changes
        """
        self.reload_category ()

    def on_drag_data_get (self, treeview, context, selection, target_id, etime):
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        #get the classname
        data = model.get_value(iter, 2)

        log.debug("Dragging %s" % data)

        selection.set(selection.target, 8, data)
        
    def on_drag_data_delete (self, context, etime):
        """
        DnD magic. do not touch
        """
        self.tree.emit_stop_by_name('drag-data-delete')      

    def get_current_category (self):
        """
        Return the currently selected category name
        """
        iter = self.combo.get_active_iter ()

        if not iter:
            return None

        return self.combo.get_model().get_value (iter, 0)

    def reload_category_if_current (self, category_name):
        """
        Only reloads the category if the given name is the current one
        """
        if category_name == self.get_current_category():
            self.reload_category()

    def reload_category (self):
        """
        Reloads the current category
        """
        category_name = self.get_current_category()
        log.info("Loading category: %s" % category_name)

        self.dp_store.clear()

        for dp in self.categories[category_name]:
            self.dp_store.append ((dp.get_descriptive_icon(), dp.name, dp.get_key()))

