"""
RTM Sync.
"""
import os, sys
import traceback
import md5
import logging
log = logging.getLogger("modules.RTM")
import dateutil
import urllib, urllib2
import vobject
import itertools
import conduit
import conduit.utils as Utils
import conduit.Web as Web
import conduit.datatypes.Event as Event
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.dataproviders.DataProvider as DataProvider

from gettext import gettext as _
Utils.dataprovider_add_dir_to_path(__file__)
import rtm
MODULES = {
    "RTMTasksTwoWay" : {"type":"dataprovider" }
}

class RTMTasksTwoWay(DataProvider.TwoWay):

    DEFAULT_TASK_URI = "default"

    _name_ = _("Remember The Milk Tasks")
    _description_ = _("Synchronize your tasks to Remember The Milk")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _configurable_ = True
    _module_type_ = "twoway"
    _in_type_ = "event"
    _out_type_ = "event"
    _icon_ = "tomboy"
    
    API_KEY = 'fe049e2cec86568f3d79c964d4a45f5c'
    SECRET='b57757de51f7e919'
    
    def __init__(self, *args):
        DataProvider.TwoWay.__init__(self)
        self.uids = None
        self.tasks = {}
        self.ical = None
        self.username = ""
        self.password = ""
        self.token = ""
        self.rtm = rtm.RTM(apiKey=self.API_KEY,secret=self.SECRET,token=self.get_configuration().get('token'))

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        self.tasks = {}
        tempt = rtm.get_all_tasks(self.rtm)
        #self.tasks.sort(key='id')
        self.ical =open(urllib.urlretrieve('http://%s:%s@www.rememberthemilk.com/icalendar/%s/events/'%(
        self.get_configuration().get('username'),
        self.get_configuration().get('password'),
        self.get_configuration().get('username')))[0]).read()
    
        for t in tempt:
            self.tasks[t.id] = t
            
    
    def get_all(self):
        return list(self.tasks.iterkeys())

    def get (self, LUID):
        log.warn("LUID: %s" % LUID)
        task = None
        if self.tasks.has_key(LUID):
            task = self.tasks[LUID]
        else:
            self.refresh()
            if self.tasks.has_key(LUID):
                task = self.tasks[LUID]
            else :
                task = None
        e = Event.Event()
        e.set_UID(self.get_UID())
        e.set_mtime( dateutil.parser.parse(task.modified))
        e.set_open_URI('http://www.rememberthemilk.com/home/%s/#%s'%(self.username,task.id))
        res = [sum for sum in vobject.readComponents(self.ical) if sum.vevent.summary.value  == task.name]
        e.set_from_ical_string(res[0].serialize())
        return e
            

    def delete(self, LUID):
        self.rtm.tasks.delete(task_id=LUID)
        del self.tasks[LUID]
    
    def put(self, putData, overwrite, LUID):
        raise NotImplementedError("Not done")
    
    #----------------------------------------------------------------------
    def get_UID(self):
        return "RTM#%s"%(self.get_configuration().get("username"))

    def _login(self):
        if self.token is None:
            # get the ticket and open login url
            #self.token = self.rtm.getToken()
            url = self.rtm.getAuthURL()

            #wait for log in
            Web.LoginMagic("Log into RememberTheMilk", url, login_function=self._try_login)

    def _try_login (self):
        """
        Try to perform a login, return None if it does not succeed
        """
        try:
            self.token = self.rtm.getToken()
            return self.token
        except:
            return None

    def configure(self, window):
        """
        Configures the RTM Backend
        """
        import gtk
        import gobject
        def on_login_finish(*args):
            Utils.dialog_reset_cursor(dlg)
            
        def on_response(sender, responseID):
            if responseID == gtk.RESPONSE_OK:
                self.username = str(tree.get_widget('user_entry').get_text())
                self.password = str(tree.get_widget('pass_entry').get_text())
                
        def load_button_clicked(button):
            Utils.dialog_set_busy_cursor(dlg)
            conduit.GLOBALS.syncManager.run_blocking_dataprovider_function_calls(
                                            self,
                                            on_login_finish,
                                            self._login)


        tree = Utils.dataprovider_glade_get_widget(
                        __file__,
                        "config.glade",
                        "RTMConfigDialog")

        #get a whole bunch of widgets
        load_button = tree.get_widget("load_button")
        dlg = tree.get_widget("RTMConfigDialog")

        # load button
        load_button.connect('clicked', load_button_clicked)

        # run the dialog
        Utils.run_dialog_non_blocking(dlg, on_response, window)

    def is_configured (self, isSource, isTwoWay):
        return self.token is not None

    def get_configuration(self):
        return {
            "token" : self.token,
            "username" : self.username,
            "password" : self.password
        }
    
  

