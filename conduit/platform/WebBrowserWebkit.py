import webkit
import conduit.platform

class WebBrowserImpl(conduit.platform.WebBrowser):
    def __init__(self):
        conduit.platform.WebBrowser.__init__(self)
        self.webView = webkit.WebView()

    def widget(self):
        return self.webView
 
    def load_url(self,url):
        self.webView.open(url)

    def stop_load(self):
        self.webView.stop_loading()

