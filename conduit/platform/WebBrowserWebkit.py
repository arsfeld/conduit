import gtk
import webkit
import conduit.platform

class WebBrowserImpl(conduit.platform.WebBrowser):
    def __init__(self):
        conduit.platform.WebBrowser.__init__(self)
        self.sw = gtk.ScrolledWindow()
        self.sw.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
        self.webView = webkit.WebView()
        self.webView.get_settings().props.enable_plugins = False
        self.sw.add(self.webView)

    def widget(self):
        return self.sw
 
    def load_url(self,url):
        self.webView.open(url)

    def stop_load(self):
        self.webView.stop_loading()

