
class Error(Exception):
    pass

class BaseProperty(object):
    
    def __init__(self, default, kind = None, persistent = True):
        self._name = None
        self.default = default
        self.kind = kind
        self.persistent = persistent
    
    def __get__(self, instance, cls):
        if not instance:
            raise Error("Properties cannot be accessed without an instance")
        name = self._find_name(cls)
        if not name in instance.__dict__:
            instance.__dict__[name] = self.default
        return instance.__dict__[name]
    
    def __set__(self, instance, value):
        name = self._find_name(type(instance))
        instance.__dict__[] = value
    
    def _find_name(self, cls):
        if not self._name:
            self_id = id(self)
            for name, prop in cls.__dict__.iteritems():
                if id(prop) == self_id:
                    self._name = name
                    break
        return self._name
