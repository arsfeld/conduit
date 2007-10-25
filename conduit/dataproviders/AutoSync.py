import gobject

class AutoSync(object):

    def __init__(self):
        self.as_added = []
        self.as_modified = []
        self.as_deleted = []
        self.timeout = 5
        self._timeout_id = 0

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
        print self._get_changes()

    def _get_changes(self):
        return self.as_added, self.as_modified, self.as_deleted
