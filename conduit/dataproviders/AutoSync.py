import gobject
from types import MethodType
import logging
log = logging.getLogger("dataproviders.AutoSync")

class AutoSync(object): 
    def __init__(self): pass
    def handle_added(self, uid): pass
    def handle_modified(self, uid): pass
    def handle_deleted(self, uid): pass

class BrokenAutoSync(object):
    def __init__(self):
        self.as_added = []
        self.as_modified = []
        self.as_deleted = []
        self.timeout = 5
        self._timeout_id = 0

        self.first_sync = True

        # decorate functions
        self.get_changes = self.decorated_changes(self.get_changes)
        self.finish = self.decorated_finish(self.finish)

    def handle_added(self, uid):
        if not uid in self.as_added and not uid in self.as_modified:
            if uid in self.as_deleted:
                self.as_deleted.remove(uid)
                self.as_modified.append(uid)
            else:    
                self.as_added.append(uid)
            self._handle_change()

    def handle_modified(self, uid):
        if not uid in self.as_modified and not uid in self.as_deleted and not uid in self.as_added:
            self.as_modified.append(uid)
            self._handle_change()

    def handle_deleted(self, uid):
        if not uid in self.as_deleted:
            if uid in self.as_added:
                self.as_added.remove(uid)
            else:
                if uid in self.as_modified:
                    self.as_modified.remove(uid)
                self.as_deleted.append(uid)
            self._handle_change()

    def _handle_change(self):
        # reset timer..
        if self._timeout_id > 0:
            gobject.source_remove(self._timeout_id)
            self._timeout_id = 0

        # add a new one, or trigger sync immediately
        if self.timeout > 0:
            self._timeout_id = gobject.timeout_add(self.timeout * 1000, self._handle_sync)
        else:
            self.emit_change_detected()

    def _handle_sync(self):
        self._timeout_id = 0
        self.emit_change_detected()

    def decorated_changes(self, old_func):
        def _get_changes(self):
            if self.first_sync == True:
                return old_func()
            else:
                return self.as_added, self.as_modified, self.as_deleted
        return MethodType(_get_changes, self)

    def decorated_finish(self, old_func):
        # Ugly, only needed until we use super() ;-)
        def _finish(self):
            #FIXME: Only do on a succesfull sync
            self.first_sync = False
            old_func()
        return MethodType(_finish, self)
        
