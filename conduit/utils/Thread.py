import time
import threading
import conduit

class PauseCancelThread(threading.Thread):
    SLEEP_TIME = 20
    SLEEP = 0.1
    def __init__(self):
        threading.Thread.__init__(self)
        self._cancelled = False

    def run(self):
        raise NotImplementedError

    def pause(self):
        i = 0
        while ( i < (self.SLEEP_TIME/self.SLEEP) ) and ( self.is_cancelled() == False ):
            time.sleep(self.SLEEP)
            i += 1

    def is_cancelled(self):
        return conduit.GLOBALS.cancelled or self._cancelled

    def cancel(self):
        self._cancelled = True

