"""
Functions for dealing with web urls, generally used for
logging into web sites for authorization
"""
import sys
import os
import gobject
import time
import thread
import logging
log = logging.getLogger("Web")

import conduit
import conduit.utils.Singleton as Singleton
import conduit.platform.WebBrowserSystem as WebBrowserSystem

class LoginWindow(Singleton.Singleton):
    """
    The ConduitLogin object needs to be a singleton so that we
    only have one window with multiple tabs, and so we can guarentee
    that it runs in the GUI thread
    """

    def __init__(self):
        self.window = None
        self.notebook = None
        self.pages = {}
        self.finished = {}

        log.debug("Created login window (thread: %s)" % thread.get_ident())

    def _on_window_closed(self, *args):
        for url in self.pages.keys():
            self._delete_page(url)
        return True
            
    def _on_tab_close_clicked(self, button, url):
        self._delete_page(url)
            
    def _on_open_uri(self, *args):
        log.debug("Link clicked (thread: %s)" % thread.get_ident())

    def _delete_page(self, url):
        log.debug("Delete page (thread: %s)" % thread.get_ident())
        #get the original objects
        browser = self.pages[url]
        browserWidget = browser.widget()
        browser.stop_load()

        #remove the page and any refs
        idx = self.notebook.page_num(browserWidget)
        self.notebook.remove_page(idx)
        browserWidget.destroy()
        del(self.pages[url])

        if self.notebook.get_n_pages() == 0:
            self.window.hide()

        #notify 
        self.finished[url] = True

    def _create_page(self, name, url, browserName):
        log.debug("Create page: %s (thread: %s)" % (url,thread.get_ident()))
        if url in self.pages:
            return False

        import gtk
        if browserName == "gtkmozembed":
            import conduit.platform.WebBrowserMozilla as WebBrowserImpl
        elif browserName == "webkit":
            import conduit.platform.WebBrowserWebkit as WebBrowserImpl

        #lazy init to save a bit of time
        if self.window == None:
            self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.window.set_title("Conduit Login Manager")
            self.window.set_border_width(12)
            self.window.connect('delete-event', self._on_window_closed)
            self.notebook = gtk.Notebook()
            self.window.add(self.notebook)

        self.window.set_default_size(700, 600)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.show_all()

        #create object and connect signals
        browser = WebBrowserImpl.WebBrowserImpl()
        browser.connect("open_uri",self._on_open_uri)

        #create the tab label
        tab_button = gtk.Button()
        tab_button.connect('clicked', self._on_tab_close_clicked, url)
        tab_label = gtk.Label(name)
        tab_box = gtk.HBox(False, 2)
        #Add icon to button
        icon_box = gtk.HBox(False, 0)
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        tab_button.set_relief(gtk.RELIEF_NONE)
        icon_box.pack_start(image, True, False, 0)
        tab_button.add(icon_box)
        tab_box.pack_start(tab_label, False)
        tab_box.pack_start(tab_button, False)
        tab_box.show_all()

        #add to notebook
        browserWidget = browser.widget()
        browserWidget.show_now()
        self.notebook.append_page(child=browserWidget, tab_label=tab_box)
        self.notebook.show_all()
        self.pages[url] = browser

        browser.load_url(url)
        return False

    def _raise_page(self, url):
        log.debug("Raise page (thread: %s)" % thread.get_ident())
        self.window.show_all()

        #get the original objects
        browser = self.pages[url]
        browserWidget = browser.widget()

        #make page current
        idx = self.notebook.page_num(browserWidget)
        self.notebook.set_current_page(idx)

        #show            
        browserWidget.show_now()
        return False

    def wait_for_login(self, name, url, **kwargs):
        log.debug("Wait for login (thread: %s)" % thread.get_ident())
    
        if url in self.pages:
            gobject.idle_add(self._raise_page, url)
        else:
            gobject.idle_add(self._create_page, name, url, kwargs["browserName"])
            self.finished[url] = False

        while not self.finished[url] and not conduit.GLOBALS.cancelled:
            #We can/need to sleep here because the GUI work is going on in the main thread
            #and gtk.main needs to iterate
            time.sleep(0.1)

        log.debug("Finished login (thread: %s)" % thread.get_ident())

        #call the test function
        testFunc = kwargs.get("login_function",None)
        if testFunc != None and testFunc():
            return
        else:
            raise Exception("Login failure")
            
class LoginMagic(object):
    """
    Performs all the magic to log into a website to authenticate. Uses
    either the system browser, or conduits own one.
    """
    def __init__(self, name, url, **kwargs):
        browser = kwargs.get("browser",conduit.BROWSER_IMPL)
        log.info("Logging in using browser: %s (thread: %s)" % (browser,thread.get_ident()))

        #instantiate the browser
        if browser == "system":
            login = WebBrowserSystem.WebBrowserImpl()
        else:
            try:
                if browser not in ("gtkmozembed","webkit"):
                    log.warn("Unknown browser type")
                    return

                kwargs["browserName"] = browser
                login = LoginWindow()

            except ImportError:
                login = None

        if login:
            #blocks/times out until the user logs in or gives up        
            login.wait_for_login(name, url, **kwargs)
        else:
            log.warn("Error setting up browser")
            

