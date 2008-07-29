import os.path
import gtkmozembed

import logging
log = logging.getLogger("WebBrowser")

import conduit.platform
import conduit.utils.Singleton as Singleton

class _MozConfig(Singleton.Singleton):
    """
    A Singleton whose only responsibilty is to configure gtkmozembed to
    use the correct profile path. Gtkmozembed only allows its profile
    path to be set once
    """

    DEFAULT_PROFILE = 'default'

    def __init__(self, **kwargs):
        self._profile = kwargs.get('profile', self.DEFAULT_PROFILE)
        self._profileDir = kwargs.get('profileDir', self._get_profile_subdir())

        log.info("Configuring Mozilla profile dir")

        self._create_prefs_js()
        gtkmozembed.set_profile_path(self._profileDir, self._profile)

    def _get_profile_subdir(self):
        """
        Some webbrowsers need a profile dir. Make it if
        it doesnt exist
        """
        subdir = os.path.join(conduit.USER_DIR, 'mozilla')
        profdir = os.path.join(subdir, self._profile)
        if not os.access(profdir, os.F_OK):
            os.makedirs(profdir)
        return subdir

    def _create_prefs_js(self):
        """
        Create the file prefs.js in the mozilla profile directory.  This
        file does things like turn off the warning when navigating to https pages.
        """
        prefsContent = """\
# Mozilla User Preferences
user_pref("security.warn_entering_secure", false);
user_pref("security.warn_entering_weak", false);
user_pref("security.warn_viewing_mixed", false);
user_pref("security.warn_leaving_secure", false);
user_pref("security.warn_submit_insecure", false);
user_pref("security.warn_entering_secure.show_once", false);
user_pref("security.warn_entering_weak.show_once", false);
user_pref("security.warn_viewing_mixed.show_once", false);
user_pref("security.warn_leaving_secure.show_once", false);
user_pref("security.warn_submit_insecure.show_once", false);
user_pref("security.enable_java", false);
user_pref("browser.xul.error_pages.enabled", false);
user_pref("general.useragent.vendor", "%s");
user_pref("general.useragent.vendorSub", "%s");
user_pref("general.useragent.vendorComment", "%s");
""" % ("Conduit",conduit.VERSION,"http://www.conduit-project.org")

        if conduit.GLOBALS.settings.proxy_enabled():
            log.info("Setting mozilla proxy details")
            host,port,user,password = conduit.GLOBALS.settings.get_proxy()
            prefsContent += """\
user_pref("network.proxy.type", 1);
user_pref("network.proxy.http", "%s");
user_pref("network.proxy.http_port", %d);
user_pref("network.proxy.ssl", "%s");
user_pref("network.proxy.ssl_port", %s);
user_pref("network.proxy.share_proxy_settings", true);
""" % (host,port,host,port)

        prefsPath = os.path.join(self._profileDir,self._profile,'prefs.js')
        f = open(prefsPath, "wt")
        f.write(prefsContent)
        f.close()

class WebBrowserImpl(conduit.platform.WebBrowser):
    """
    Wraps the GTK embeddable Mozilla in the WebBrowser interface
    """
    def __init__(self, **kwargs):
        conduit.platform.WebBrowser.__init__(self)

        #lazy import and other hoops necessary because
        self._mozconfig = _MozConfig(**kwargs)

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

