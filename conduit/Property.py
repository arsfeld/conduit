import sys
import logging
log = logging.getLogger("Property")

from gettext import gettext as _ 

class Error(Exception):
    pass

class PropertyBase(object):
    
    def __init__(self, default, kind = None, title = None, persistent = True, config_name = None, **kwargs):
        self.name = None
        self.default = default
        self.kind = kind
        self.title = title
        self.persistent = persistent
        log.critical("config_name %s" % (config_name))
        #if persistent or config_name:
        self.config_name = config_name
        #else:
        #    self.config_name = None
        kwargs['persistent'] = persistent
        self.kwargs = kwargs

    def _set_name(self, name):
        self.name = name
        log.critical("Found name %s (config_name: %s, title: %s)" % (self.name, self.config_name, self.title))
        if not self.title:
            self.title = self.name.capitalize().replace("_", " ")
            log.critical("> Setting title: %s" % self.title)
        if not self.config_name: # and self.persistent:
            self.config_name = self.name
            log.critical("> Setting config_name: %s" % self.config_name)
        #log.critical("Found name %s (config_name: %s, title: %s)" % (self.name, self.config_name, self.title))
        
    def __get__(self, instance, cls):
        if not instance:
            #raise Error("Properties cannot be accessed without an instance")
            return self
        name = self.find_name(cls)
        if not name in instance.__dict__:
            instance.__dict__[name] = self.default
        return instance.__dict__[name]
    
    def __set__(self, instance, value):
        name = self.find_name(type(instance))
        instance.__dict__[name] = value
    
    def find_name(self, cls):
        if not self.name:
            self_id = id(self)
            for name, prop in cls.__dict__.iteritems():
                if id(prop) == self_id:
                    self._set_name(name)
                    break
        return self.name
