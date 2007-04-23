import os
import sys
import traceback
import gtk
from gettext import gettext as _


import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note

Utils.dataprovider_add_dir_to_path(__file__, "backpack-1.1")
import backpack

MODULES = {
	"BackpackNoteSink" : { "type": "dataprovider" }
}

BACKPACK_CAT = DataProvider.DataProviderCategory("Backpackit.com","backpack")

class BackpackBase(DataProvider.DataProviderBase):
    """
    Simple wrapper to share gmail login stuff
    """
    def __init__(self, *args):
        self.username = ""
        self.apikey = ""

        self.ba = None

    def initialize(self):
        return True
    
    def refresh(self):
        username = "http://" + self.username + ".backpackit.com/"
        try:
            self.ba = backpack.Backpack(username,self.apikey)
            self.loggedIn = True
        except backpack.BackpackError:
            logw("Error logging into backpack (username %s)" % self.username)
            raise Exceptions.RefreshError
    

class BackpackNoteSink(BackpackBase, DataProvider.DataSink):

    _name_ = _("Backpack Notes")
    _description_ = _("Store things in Backpack Notes")
    _category_ = BACKPACK_CAT
    _module_type_ = "sink"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "tomboy"

    def __init__(self, *args):
        BackpackBase.__init__(self, *args)
        DataProvider.DataSink.__init__(self)
        
        self.storeInPage = "Conduit"
        self.pageID = None

        #there is no way to pragmatically see if a note exists so we list them
        #and cache the results. key = note uid
        self._notes = {}

    def configure(self, window):
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "BackpackNotesSinkConfigDialog")
        
        #get a whole bunch of widgets
        usernameEntry = tree.get_widget("username")
        apikeyEntry = tree.get_widget("apikey")
        pagenameEntry = tree.get_widget("pagename")        
        
        #preload the widgets
        usernameEntry.set_text(self.username)
        pagenameEntry.set_text(self.storeInPage)        
        
        dlg = tree.get_widget("BackpackNotesSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            self.username = usernameEntry.get_text()
            self.storeInPage = pagenameEntry.get_text()
            if apikeyEntry.get_text() != self.apikey:
                self.apikey = apikeyEntry.get_text()
        dlg.destroy()    
        
        
    def put(self, note, overwrite, LUID=None):
        DataProvider.DataSink.put(self, note, overwrite, LUID)
        #First search for the pageID of the named page to put notes in
        if self.pageID is None:
            pages = self.ba.page.list()
            for uid,scope,title in pages:
                if title == self.storeInPage:
                    self.pageID = uid
                    logd("Found Page %s:%s:%s" % (uid,scope,title))
            #Didnt find the page so create
            if self.pageID is None:
                try:
                    self.pageID, foo = self.ba.page.create(self.storeInPage,"Automatically Synchronized Notes")
                    log("Created page")
                except backpack.BackpackError, err:
                    log("Could not create page to store notes in (%s)" % err)
                    #cannot continue
                    raise Exceptions.SyncronizeFatalError
                    
        #First put needs to cache the existing note titles and uris
        if len(self._notes) == 0:
            for uid, title, timestamp, text in self.ba.notes.list(self.pageID):
                self._notes[title] = uid
            logd("Found existing notes: %s" % self._notes)
        
        #FIXME: implement overwrite and LUID behaviour

        #If all that went well then actually store some notes.
        uid = None
        try:
            if note.title in self._notes:
                logd("Updating Existing")
                uid = self._notes[note.title]
                self.ba.notes.update(self.pageID,uid,note.title,note.contents)
            else:
                logd("Creating New")
                uid,title,mtime,content = self.ba.notes.create(self.pageID,note.title,note.contents)
                self._notes[note.title] = uid
        except backpack.BackpackError, err:
            log("Could not sync note (%s)" % err)
            raise Exceptions.SyncronizeError
                
        return uid

    def get_configuration(self):
        return {
            "storeInPage" : self.storeInPage,
            "username" : self.username,
            "apikey" : self.apikey
            }
