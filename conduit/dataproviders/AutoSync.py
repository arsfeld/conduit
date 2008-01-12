import gobject
import logging
log = logging.getLogger("dataproviders.AutoSync")

class AutoSync(object):
    def __init__(self):
        self.timeout = 5
        self._timeout_id = 0

    def handle_added(self, uid):
        self._handle_change()

    def handle_modified(self, uid):
        self._handle_change()

    def handle_deleted(self, uid):
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

