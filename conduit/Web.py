"""
Functions for dealing with web urls, generally used for
logging into web sites for authorization
"""
import os
import gobject
import webbrowser
import time
import thread

import conduit
from conduit import logd

def open_url(url):
    logd("Opening %s" % url)
    webbrowser.open(url,new=1,autoraise=True)
    logd("Opened %s" % url)

def get_profile_subdir(subdir):
    """
    Some webbrowsers need a profile dir. Make it if
    it doesnt exist
    """
    profdir = os.path.join(conduit.USER_DIR, subdir)
    if not os.access(profdir, os.F_OK):
        os.makedirs(profdir)
    return profdir

class _WebBrowser(gobject.GObject):
    """
    Basic webbrowser abstraction to provide an upgrade path
    to webkit from gtkmozembed
    """
    __gsignals__ = {
        "location_changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING]),      # The new location
        "loading_started" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "loading_finished" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "loading_progress" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_FLOAT]),       # -1 (unknown), 0 -> 1 (finished)
        "status_changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING]),      # The status
        "open_uri": (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING])       # URI
        }
    def __init__(self, emitOnIdle=False):
        gobject.GObject.__init__(self)
        self.emitOnIdle = emitOnIdle

    def emit(self, *args):
        """
        Override the gobject signal emission so that signals
        can be emitted from the main loop on an idle handler
        """
        print "------EMITTING: %s" % args[0]
        if self.emitOnIdle == True:
            gobject.idle_add(gobject.GObject.emit,self,*args)
        else:
            gobject.GObject.emit(self,*args)

    def load_url(self, url):
        raise NotImplementedError

    def stop_load(self):
        raise NotImplementedError

class _MozEmbedWebBrowser(_WebBrowser):
    """
    Wraps the GTK embeddable Mozilla in the WebBrowser interface
    """
    import gtkmozembed
    global gtkmozembed
    #set_profile_path is here so it only gets called once
    gtkmozembed.set_profile_path(get_profile_subdir('mozilla'), 'default')

    def __init__(self):
        _WebBrowser.__init__(self)
        self.url_load_request = False # flag to break load_url recursion
        self.location = ""

        self.moz = gtkmozembed.MozEmbed()
        self.moz.connect("link-message", self._signal_link_message)
        self.moz.connect("open-uri", self._signal_open_uri)
        self.moz.connect("location", self._signal_location)
        self.moz.connect("progress", self._signal_progress)
        self.moz.connect("net-start", self._signal_net_start)
        self.moz.connect("net-stop", self._signal_net_stop)

    def widget(self):
        return self.moz

    def load_url(self, str):
        self.url_load_request = True  # don't handle open-uri signal
        self.moz.load_url(str)        # emits open-uri signal
        self.url_load_request = False # handle open-uri again

    def stop_load(self):
        self.moz.stop_load()

    def _signal_link_message(self, object):
        self.emit("status_changed", self.moz.get_link_message())

    def _signal_open_uri(self, object, uri):
        if self.url_load_request: 
            return False # proceed as requested
        else:
            return self.emit("open_uri", uri)
        
    def _signal_location(self, object):
        self.location_changed(self.moz.get_location())

    def location_changed(self, location):
        self.location = location
        self.emit("location_changed",self.location)

    def _signal_progress(self, object, cur, maxim):
        if maxim < 1:
            self.emit("loading_progress", -1.0)
        else:
            self.emit("loading_progress", (cur/maxim))

    def _signal_net_start(self, object):
        self.emit("loading_started")

    def _signal_net_stop(self, object):
        self.emit("loading_finished")

    def __del__(self):
        print "---------IF WEIRD THINGS HAPPEN ITS BECAUSE I WAS GC'd TO EARLY-------------------------"

class _SystemLogin(object):
    def __init__ (self):
        pass
        
    def wait_for_login(self, name, url, **kwargs):
        self.testFunc = kwargs.get("login_function",None)
        self.timeout = kwargs.get("timeout",30)
    
        #use the system web browerser to open the url
        logd("System Login for %s" % name)
        open_url(url)

        start_time = time.time()
        while not self._is_timed_out(start_time):
            try:
                if self.testFunc():
                    return
            except Exception, e:
                logd("testFunc threw an error: %s" % e)
                pass

            time.sleep(2)

        raise Exception("Login timed out")

    def _is_timed_out(self, start):
        return int(time.time() - start) > self.timeout

class _ConduitLoginSingleton(object):
    def __init__(self):
        self.window = None
        self.notebook = None
        self.pages = {}
        self.finished = {}

    def _on_window_closed(self, *args):
        for url in self.pages.keys():
            self._delete_page(url)
        return True
            
    def _on_tab_close_clicked(self, button, url):
        self._delete_page(url)
            
    def _build_browser(self, browserName):
        if browserName == "gtkmozembed":
            browser = _MozEmbedWebBrowser()
        #
        #IMPLEMENT OTHER WEB BROWSERS HERE
        #
        #elif browserName == "webkit":
        #    browser = _GtkHtmlWebBrowser(get_profile_subdir('webkit'))
        else:
            raise Exception("Unknown browser: %s" % browserName)

        return browser

    def _on_open_uri(self, *args):
        print "LINK CLICKED ----------------------------", thread.get_ident()

    def _delete_page(self, url):
        print "DELETE PAGE ----------------------------", thread.get_ident()
        #get the original objects
        browser = self.pages[url]
        browserWidget = browser.widget()
        browser.stop_load()

        #remove the page and any refs
        idx = self.notebook.page_num(browserWidget)
        self.notebook.remove_page(idx)
        del(self.pages[url])

        if self.notebook.get_n_pages() == 0:
            self.window.hide_all()

        #notify 
        self.finished[url] = True

    def _create_page(self, name, url, browserName):
        print "CREATE PAGE ----------------------------", thread.get_ident(), url
        if url in self.pages:
            return False

        import gtk
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

        #create object and connect signals
        browser = self._build_browser(browserName)
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
        self.notebook.append_page(child=browserWidget, tab_label=tab_box)
        self.pages[url] = browser

        browserWidget.show_now()
        self.window.show_all()
        browser.load_url(url)

        return False

    def _raise_page(self, url):
        print "RAISE PAGE ----------------------------", thread.get_ident()
        #get the original objects
        browser = self.pages[url]
        browserWidget = browser.widget()

        #make page current
        idx = self.notebook.page_num(browserWidget)
        self.notebook.set_current_page(idx)

        #show            
        browserWidget.show_now()
        self.window.show_all()

        return False

    def wait_for_login(self, name, url, **kwargs):
        print "LOGIN ----------------------------", thread.get_ident()
    
        if url in self.pages:
            gobject.idle_add(self._raise_page, url)
        else:
            browserName = kwargs.get("browser",conduit.GLOBALS.settings.get("web_login_browser"))
            gobject.idle_add(self._create_page, name, url, browserName)
            self.finished[url] = False

        while not self.finished[url]:
            #We can sleep here because all the GUI work
            #is going on in the main thread
            time.sleep(0.5)
            print '. ', thread.get_ident()

        print "FINISHED LOGIN ----------------------------", thread.get_ident()

        #call the test function
        testFunc = kwargs.get("login_function",None)
        if testFunc != None and testFunc():
            return
        else:
            raise Exception("Login failure")
            
#The ConduitLogin object needs to be a singleton so that we
#only have one window with multiple tabs, and so we can guarentee
#that it runs in the GUI thread
_ConduitLogin = _ConduitLoginSingleton()

class LoginMagic(object):
    """
    Performs all the magic to log into a website to authenticate. Uses
    either the system browser, or conduits own one.
    """
    def __init__(self, name, url, **kwargs):
        browser = kwargs.get("browser",conduit.GLOBALS.settings.get("web_login_browser"))
        #instantiate the browser
        if browser == "system":
            login = _SystemLogin()
        else:
            login = _ConduitLogin

        #blocks/times out until the user logs in or gives up        
        login.wait_for_login(name, url, **kwargs)

