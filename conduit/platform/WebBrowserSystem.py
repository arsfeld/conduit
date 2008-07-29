import time
import webbrowser
import logging
log = logging.getLogger("WebBrowser")

import conduit.platform

class WebBrowserImpl(conduit.platform.WebBrowser):
    def __init__(self, **kwargs):
        conduit.platform.WebBrowser.__init__(self)

    def wait_for_login(self, name, url, **kwargs):
        self.testFunc = kwargs.get("login_function",None)
        self.timeout = kwargs.get("timeout",30)
    
        #use the system web browerser to open the url
        log.debug("System Login for %s" % name)
        webbrowser.open(url,new=1,autoraise=True)

        start_time = time.time()
        while not self._is_timed_out(start_time):
            time.sleep(kwargs.get("sleep_time",2))        
            try:
                if self.testFunc():
                    return
            except Exception, e:
                log.debug("Login function threw an error: %s" % e)

        raise Exception("Login timed out")

    def _is_timed_out(self, start):
        return int(time.time() - start) > self.timeout


