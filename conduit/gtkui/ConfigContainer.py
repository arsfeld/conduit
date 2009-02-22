'''Manages configuration items for a dataprovider.

The ConfigContainer should handle all widgets in a configurator, including
adding, removing and handling such as applying and cancelling the configuration.

Copyright: Alexandre Rosenfeld, 2009
License: GPLv2
'''

import sys
import sets
import gobject
import gtk, gtk.glade
import logging
log = logging.getLogger("gtkui.ConfigContainer")

from gettext import gettext as _ 
import conduit
import conduit.gtkui.ConfigItems as ConfigItems
import conduit.Configurator as Configurator

class Error(Exception):
  """Base exception for all exceptions raised in this module."""
  pass

class ConfigContainer(Configurator.BaseConfigContainer):
    """
    Gtk implementation to the ConfigController.
    
    A dataprovider usually does not need to instantiate this class.
    """
    
    __gsignals__ = {
        'item-changed' : (gobject.SIGNAL_RUN_FIRST, None, (gobject.TYPE_OBJECT,)),
    }

    def __init__(self, dataprovider, configurator):
        super(ConfigContainer, self).__init__(dataprovider, configurator)
        
        # Current section
        self.section = None
        self.sections = []
        self.items = []
        self.built_items = False
        self.config_values = None
        
        self._reset_modified_items()
        
        #the child widget to contain the custom settings
        self.widgetTable = gtk.Table(rows=1, columns=2)        
        self.widgetTable.set_row_spacings(6)
        self.widgetTable.set_col_spacings(12)
        
        self.config_widget = self.widgetTable
        
        self.firstRow = True

    def _reset_modified_items(self, empty = True):
        '''
        Reset the list of modified items. If empty is true, just create a new
        empty list of modified items (so that no item is modified).
        If empty is False, set the list to None, so that it will be recreated
        next time get_modified_items is called.
        '''
        if empty:
            self.modified_items = sets.Set()
        else:
            self.modified_items = None
        
    def _item_changed(self, item, initial_state, value):
        self.emit("item-changed", item)
        if self.modified_items is None:
            self.get_modified_items()
        if not initial_state:
            self.modified_items.add(item)
        elif item in self.modified_items:
            self.modified_items.remove(item)
        self.emit('changed', self.is_modified())
        
    def _rebuild_widgets(self):
        '''
        Rebuild widgets if needed
        '''
        self.modified_items = None
        if self.showing:
            self._build_widgets()
    
    def _build_widgets(self):
        '''
        Creates all necessary widgets
        '''
        table = self.widgetTable
        if self.showing:
            table.foreach(lambda widget: table.remove(widget))
            table.resize(1, 2)
            rows = 0
        elif self.firstRow:
            self.firstRow = False
            rows = 0
        else:
            rows = table.get_property('n-rows')            
        for section in sorted(self.sections, key = lambda section: section.order):
            rows = section.attach(table, rows)
            if rows != 1:
                table.set_row_spacing(rows - 1, 16)
        self.widgetTable.show_all()

    def _reset(self):
        '''
        Set all items to their initial state
        '''
        for item in self.items:
            item.reset()

    def add_section(self, title = None, order = 0, use_existing = True, **kwargs):
        '''
        Add a section. Returns the Section object.
        '''
        if (not title and self.section and not self.section.title) or \
           (use_existing and self.section and title is self.section.title):
            return self.section
        found = False
        if use_existing and title:  
            for section in self.sections:
                if section.title == title:
                    self.section = section
                    found = True
                    break
        if not use_existing or not found:
            self.section = ConfigItems.Section(self, title, order, **kwargs)
            self.sections.append(self.section)
        self._rebuild_widgets()
        return self.section
    
    def add_item(self, title, kind, order = 0, **kwargs):
        '''
        Add a configuration item. Returns the Item object.
        
        You can pass properties to the configuration item in kwargs.
        '''
        if not self.section:
            self.add_section()
        # If we have a saved configuration in the config dict from the dp, 
        # use it as initial value.
        if self.config_values is None:
            if self.dataprovider:
                self.config_values = self.dataprovider.get_configuration()
            else:
                self.config_values = {}        
        if kwargs.get('config_name', None):
            if kwargs['config_name'] in self.config_values:
                kwargs['initial_value'] = self.config_values[kwargs['config_name']]
            else:
                raise Error("Value for %s (configuration item %s) not found in dataprovider" % (kwargs['config_name'], title))
        if 'enabled' not in kwargs:
            kwargs['enabled'] = self.section.enabled
        try:
            item_cls = ConfigItems.ItemBase.items[kind]
        except KeyError:
            raise Error("Config kind %s not found" % kind)
        item = item_cls(container = self, title = title, order = order, **kwargs)
        item.connect("value-changed", self._item_changed)
        self.items.append(item)
        self.section.add_item(item)
        self._rebuild_widgets()
        return item
        
    def get_modified_items(self):
        '''
        Return a list of items that has been modified
        '''
        if self.modified_items is None:
            self.modified_items = sets.Set([item for item in self.items if not item.is_initial_value()])
        return self.modified_items
                
    def is_modified(self):
        '''
        Returns true if any item has been modified
        '''
        return len(self.get_modified_items()) != 0        
        
    def get_config_values(self, items):
        '''
        Returns a dict suitable to set_configuration in a data-provider.
        '''
        values = {}
        for item in items:
            config_value = item.get_config_value()
            if config_value:
                values.update(config_value)
        return values
    
    def get_config_widget(self):
        '''
        Returns the root configuration widget and
        builds the configuration widgets if needed
        '''
        if not self.built_items:
            self._build_widgets()
            self.built_items = True
        return self.config_widget
    
    def show(self):
        '''
        Show the configuration widget
        '''
        super(ConfigContainer, self).show()
        self.config_widget.show_all()
        
    def apply_config(self, items = None, sections = None):
        '''
        Save the current configuration state to the dataprovider and to each 
        item, saving any changes the user might have done.
        If items is None, all items will be applied. If sections or items are
        supplied, only these items will be applied.
        '''
        super(ConfigContainer, self).apply_config()
        if not items and not sections:
            items = self.items
        elif not items and sections:
            items = []
        if sections:
            for section in sections:
                items.extend([item for item in section.items if item not in items])
        config_values = self.get_config_values(items)
        if config_values:
            #FIXME: Remove this messsage on production
            log.debug("Applying configuration: %s" % (config_values))
            self.dataprovider.set_configuration(config_values)
        for item in items:
            item.save_state()
        if not items and not sections:
            self._reset_modified_items()
        else:
            self._reset_modified_items(False)
    
    def cancel_config(self):
        '''
        Cancel the configuration, reverting any changes the user might have done
        '''
        super(ConfigContainer, self).cancel_config()
        self._reset()
        self._reset_modified_items()
