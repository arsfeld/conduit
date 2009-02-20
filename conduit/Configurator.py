"""
Configuration interfaces

Copyright: Alexandre Rosenfeld, 2009
License: GPLv2
"""
import os.path
import gobject
import logging
log = logging.getLogger("conduit.Configutator")

from gettext import gettext as _ 
import conduit

class BaseConfigContainer(gobject.GObject):
    """
    Base configuration container class.
    """
    
    __gsignals__ = {     
        # Changed is called when the user modifies anything in the 
        # configuration dialog. The bool property is True if the values
        # are in their initial state
        'changed': (gobject.SIGNAL_RUN_FIRST, None, [bool]),
        'apply': (gobject.SIGNAL_RUN_FIRST, None, []),
        'cancel': (gobject.SIGNAL_RUN_FIRST, None, []),
        'show': (gobject.SIGNAL_RUN_FIRST, None, []),
        'hide': (gobject.SIGNAL_RUN_FIRST, None, []),
    }
    
    def __init__(self, dataprovider, configurator):
        gobject.GObject.__init__(self)
        self.showing = False
        self.dataprovider = dataprovider
        self.configurator = configurator
        self.name = None
        self.icon = None
        
    def get_name(self):
        '''
        Returns the name for this container
        '''
        #FIXME: This doesnt work, the dataprovider does not have a name, it's
        # module wrapper does. This is fixed by a hack inside the Canvas, by
        # assigning the name there, which is not ideal.
        return self.name or self.dataprovider and self.dataprovider.get_name()
    
    def get_icon(self):
        '''
        Returns a path to this configurator icon
        '''
        #FIXME: This doesnt work, the dataprovider does not have an icon, it's
        # module wrapper does. This is fixed by a hack inside the Canvas, by
        # assigning the icon there, which is not ideal.
        return self.icon or self.dataprovider and self.dataprovider.get_icon()
    
    def get_config_widget(self):
        '''
        Returns the root configuration widget
        '''
        pass
        
    def show(self):
        '''
        Show the configuration widget
        '''
        self.emit('show')
        self.showing = True
        
    def hide(self):
        '''
        Hide the configuration widget
        '''
        self.emit('hide')
        self.showing = False
        
    def apply_config(self):
        '''
        Save the current configuration state to the dataprovider.
        '''
        self.emit('apply')
    
    def cancel_config(self):
        '''
        Cancel the configuration, reverting any changes the user might have done
        '''
        self.emit('cancel')
    
    def is_modified(self):
        return False

