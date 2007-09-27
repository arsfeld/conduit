"""
Functions for dealing with web urls, generally used for
logging into web sites for authorization
"""
import os
import gtk
import gobject
import webbrowser
import time

import conduit
from conduit import logd

DEFAULT_CONDUIT_BROWSER = "gtkhtml"

def open_url(url):
    logd("Opening %s" % url)
    webbrowser.open(url,new=1,autoraise=True)

    #could also use
    #import gnome
    #gnome.url_show(url)

    logd("Opened %s" % url)

class _WebBrowser(gobject.GObject):
    """
    Basic webbrowser abstraction to provide an upgrade path
    to webkit so we dont have to depend on gtkmozembed
    """
    __gsignals__ = {
        "location_changed" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [
            gobject.TYPE_STRING]),      # The new location
        "loading_started" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
        "loading_finished" : (
            gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
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
        if self.emitOnIdle == True:
            gobject.idle_add(gobject.GObject.emit,self,*args)
        else:
            gobject.GObject.emit(self,*args)

class _WebKitWebBrowser(_WebBrowser):
    """
    Wraps the PyWebKitGtk HTML view in the WebBrowser interface
    """
    def __init__(self, userdir):
        _WebBrowser.__init__(self)

        global webkitgtk
        import webkitgtk # you'll need PyWebKitGtk

        self._page = webkitgtk.Page()
        self.location = ""

        sprefix = '_signal_'
        for method in dir(self.__class__):
            if method.startswith(sprefix):
                signal = method[len(sprefix):]
                self._page.connect(signal, getattr(self, method))

        self._scrolled_window = gtk.ScrolledWindow()
        self._scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._scrolled_window.add(self._page)

    def widget(self):
        return self._scrolled_window

    def load_url(self, url):
        self._page.open(url)
        self.location = url
        self.emit("location_changed",self.location)

    def stop_load(self):
        self._page.stop_loading()

    def render_data(self, data, base_uri, mime_type):
        ct = mime_type.split("; ")
        if len(ct) > 1:
            charset = ct[1]
        else:
            charset = "utf-8" # default

        self.emit("location_changed",base_uri)
        self._page.load_string(data, ct[0], charset, base_uri)

    def _signal_load_started(self, object, frame):
        self.emit("loading_started")
    def _signal_load_progress_changed(self, object, progress):
        pass
    def _signal_load_finished(self, object, frame):
        self.emit("loading_finished")
    def _signal_title_changed(self, object, title, uri):
        self.location = uri
        self.emit("location_changed",self.location)
    def _signal_status_bar_text_changed(self, object, text):
        pass


class _GtkHtmlWebBrowser(_WebBrowser):
    """
    Wraps the GTK HTML view in the WebBrowser interface
    """
    def __init__(self, userdir):
        _WebBrowser.__init__(self)

        global gtkhtml2
        import gtkhtml2       # you'll need Debian package python-gnome2-extras

        self._view = gtkhtml2.View()
        self._document = gtkhtml2.Document()
        self._widget = gtk.ScrolledWindow()
        self._widget.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._widget.add(self._view)
        self.location = ""

        self._view.connect("on_url", self._signal_on_url)
        self._document.connect("link_clicked", self._signal_link_clicked)
        self._document.connect("request-url", self._signal_request_url)

        self._view.set_document(self._document)

    def widget(self):
        return self._widget

    def load_url(self, url):
        res = self._open_url(self._complete_url(url))
        ct = res.info()['content-type']
        self.render_data(res.read(), res.geturl(), ct)

    def render_data(self, data, base_uri, mime_type):
        self.location = base_uri
        self.emit("location_changed", self.location)

        ct = mime_type.split("; ")
        if len(ct) > 1:
            charset = ct[1]
        else:
            charset = "utf-8" # default

        self._document.clear()
        print "clear"
        self._document.open_stream(ct[0])
        print "open"
        self._document.write_stream(data)
        print "write"
        self._document.close_stream()
        print "close"
        return

    def _signal_on_url(self, object, url):
        if url == None: url = ""
        else: url = self._complete_url(url)
        self.emit("status_changed", url)

    def _signal_link_clicked(self, object, link):
        self.emit("open_uri", self._complete_url(link))

    def _signal_request_url(self, object, url, stream):
        stream.write(self._fetch_url(self._complete_url(url)))

    def _open_url(self, url, headers=[]):
        import urllib2
        opener = urllib2.build_opener()
        opener.addheaders = [('User-agent', 'conduit')]+headers
        return opener.open(url)

    def _fetch_url(self, url, headers=[]):
        return self._open_url(url, headers).read()

    def _complete_url(self, url):
        import string, urlparse, urllib
        url = urllib.quote(url, safe=string.punctuation)
        print url
        if urlparse.urlparse(url)[0] == '':
            return urlparse.urljoin(self.location, url)
        else:
            return url
            
    def __del__(self):
        print "---------IF WEIRD THINGS HAPPEN ITS BECAUSE I WAS GC'd TO EARLY-------------------------"

    
class _MozEmbedWebBrowser(_WebBrowser):
    """
    Wraps the GTK embeddable Mozilla in the WebBrowser interface
    """
    def __init__(self, profiledir):
        _WebBrowser.__init__(self)

        global gtkmozembed
        import gtkmozembed    # you'll need Debian package python-gnome2-extras

        print "Setting Mozilla profile dir to %s name %s" % (profiledir, 'default')
        gtkmozembed.set_profile_path(profiledir, 'default')

        self.moz = gtkmozembed.MozEmbed()
        self.url_load_request = False # flag to break load_url recursion
        self.location = ""

        
        sprefix = '_signal_'
        for method in dir(self.__class__):
            if method.startswith(sprefix):
                self.moz.connect(method[len(sprefix):], getattr(self, method))

    def widget(self):
        return self.moz

    def load_url(self, str):
        self.url_load_request = True  # don't handle open-uri signal
        self.moz.load_url(str)        # emits open-uri signal
        self.url_load_request = False # handle open-uri again

    def stop_load(self):
        self.moz.stop_load()
    def go_back(self):
        self.url_load_request = True  # don't handle open-uri signal
        self.moz.go_back()
        self.url_load_request = False # handle open-uri again
    def go_forward(self):
        self.url_load_request = True  # don't handle open-uri signal
        self.moz.go_forward()
        self.url_load_request = False # handle open-uri again
    def reload(self):
        self.moz.reload(gtkmozembed.FLAG_RELOADNORMAL)

    def render_data(self, data, base_uri, mime_type):
        self.url_load_request = True  # don't handle open-uri signal

        ct = mime_type.split("; ")
        if len(ct) > 1:
            charset = ct[1]
        else:
            charset = "utf-8" # default

        self.location_changed(base_uri)

        # gtkmozembed hangs if it's fed more than 2^16 at a time
        # XXX bytes, chars?
        self.moz.open_stream(base_uri, ct[0])
        while True:
            block, data = data[:2**16], data[2**16:]
            self.moz.append_data(block, long(len(block)))
            if len(data) == 0: break
        self.moz.close_stream()

        self.url_load_request = False # handle open-uri again

    def _signal_link_message(self, object):
        self.emit("status_changed", self.moz.get_link_message())

    def _signal_open_uri(self, object, uri):
        if self.url_load_request: return False # proceed as requested
        # otherwise, this is from the page
        # print uri
        import gobject
        if uri.__class__ == gobject.GPointer:
            print "The gpointer bug, guessing...",
            uri = self.moz.get_link_message()
            if uri=="": print "<empty>",
            print uri
            if uri=="":
                return False # XXX can't handle, let MozEmbed do it
            return self.emit("open_uri", uri)
        else:
            print "No gpointer bug here !-)"
            return self.emit("open_uri", uri)
        
    def _signal_location(self, object):
        self.location_changed(self.moz.get_location())

    def location_changed(self, location):
        print "moz: location: "+location
        self.location = location
        self.emit("location_changed",self.location)

    def _signal_progress(self, object, cur, maxim):
        if maxim < 1:
            print "Progress: %d" % cur
        else:
            print 'Progress: %d%%' % (cur/maxim)
    def _signal_net_state(self, object, flags, status):
        print 'net-state flags=%x status=%x' % (flags,status)
    def _signal_new_window(self, object, *args):
        print 'new-window', args
    def _signal_net_start(self, object):
        self.emit("loading_started")
    def _signal_net_stop(self, object):
        self.emit("loading_finished")
        
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

    def _build_login_window(self):
        if self.window == None:
            #build the gui and connect the close button
            self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            self.window.set_title("Conduit Login Manager")
            self.window.set_border_width(12)
            self.window.set_default_size(700, 600)
            self.window.set_position(gtk.WIN_POS_CENTER)
            self.window.connect('delete-event', self._on_window_closed)
            
            #add a notebook to hold the tabs waiting to log in
            self.notebook = gtk.Notebook()
            self.window.add(self.notebook)

    def _on_window_closed(self, *args):
        #dont distroy the window
        self.window.hide()
        return True
            
    def _on_tab_closed(self, button):
        pass
            
    def _append_page(self, name, url, browser):
        browserWidget = browser.widget()
        tab_button = gtk.Button()
        tab_button.connect('clicked', self._on_tab_closed)
        tab_label = gtk.Label(name)
        tab_box = gtk.HBox(False, 2)
        #Add icon to button
        icon_box = gtk.HBox(False, 0)
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        tab_button.set_relief(gtk.RELIEF_NONE)
        icon_box.pack_start(image, True, False, 0)
        #pack
        tab_button.add(icon_box)
        tab_box.pack_start(tab_label, False)
        tab_box.pack_start(tab_button, False)
        tab_box.show_all()
        #add to notebook
        self.notebook.append_page(child=browserWidget, tab_label=tab_box)
        self.pages[url] = browser
        
    def _build_browser(self, browserName):
        if browserName == "gtkmozembed":
            browser = _MozEmbedWebBrowser(self._get_profile_subdir('mozilla'))
        elif browserName == "webkit":
            browser = _GtkHtmlWebBrowser(self._get_profile_subdir('webkit'))
        elif browserName == "gtkhtml":
            browser = _GtkHtmlWebBrowser(self._get_profile_subdir('gtkhtml'))
        else:
            raise Exception("Unknown browser: %s" % browserName)

        return browser

    def _on_close_clicked(self):
        pass

    def _get_profile_subdir(self,subdir=''):
        """
        Some webbrowsers need a profile dir. Make it if
        it doesnt exist
        """
        profdir = os.path.join(conduit.USER_DIR, subdir)
        if not os.access(profdir, os.F_OK):
            os.makedirs(profdir)
        return profdir

    def _on_open_uri(self, *args):
        print "CLICKED"

    def wait_for_login(self, name, url, **kwargs):
        #lazily build/init the login window
        self._build_login_window()
    
        if url in self.pages:
            #get the original objects
            browser = self.pages[url]
            browserWidget = browser.widget()

            #make page current
            idx = self.notebook.page_num(browserWidget)
            self.notebook.set_current_page(idx)

            #show            
            browserWidget.show()
            self.window.show_all()
        else:
            browserName = kwargs.get("browser",conduit.GLOBALS.settings.get("web_login_browser"))
            
            browser = self._build_browser(browserName)
            #FIXME: connect all signals, and work out how to detect login
            browser.connect("open_uri",self._on_open_uri)
            #FIXME: in append page store the child widget becaue ids are not unique
            self._append_page(name, url, browser)
            self.window.show_all()
            browser.load_url(url)
            
#The ConduitLogin object needs to be a singleton so that we
#only have one window with multiple tabs
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

