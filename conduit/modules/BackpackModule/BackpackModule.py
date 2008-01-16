import os
import sys
import traceback
from gettext import gettext as _
import logging
log = logging.getLogger("modules.Backpack")

import conduit
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Note as Note

Utils.dataprovider_add_dir_to_path(__file__, "backpack")
import backpack

MODULES = {
	"BackpackNoteSink" : { "type": "dataprovider" }
}

class BackpackBase(DataProvider.DataProviderBase):
    def __init__(self, *args):
        DataProvider.DataProviderBase.__init__(self)
        self.username = ""
        self.apikey = ""
        self.ba = None
        self.loggedIn = False

    def initialize(self):
        return True
    
    def refresh(self):
        if self.loggedIn == False:
            username = "http://" + self.username + ".backpackit.com/"
            try:
                self.ba = backpack.Backpack(username,self.apikey)
                self.loggedIn = True
            except backpack.BackpackError:
                log.warn("Error logging into backpack (username %s)" % self.username)
                raise Exceptions.RefreshError
    

class BackpackNoteSink(DataProvider.DataSink, BackpackBase):

    _name_ = _("Backpack Notes")
    _description_ = _("Store things in Backpack Notes")
    _category_ = conduit.dataproviders.CATEGORY_NOTES
    _module_type_ = "sink"
    _in_type_ = "note"
    _out_type_ = "note"
    _icon_ = "backpack"

    def __init__(self, *args):
        DataProvider.DataSink.__init__(self)
        BackpackBase.__init__(self, *args)
        self.need_configuration(True)
        
        self.storeInPage = "Conduit"
        self.pageID = None
        #there is no way to pragmatically see if a note exists so we list them
        #and cache the results. key = note uid
        self._notes = {}

    def refresh(self):
        DataProvider.DataSink.refresh(self)
        BackpackBase.refresh(self)
        #First search for the pageID of the named page to put notes in
        if self.pageID is None:
            pages = self.ba.page.list()
            for uid,scope,title in pages:
                if title == self.storeInPage:
                    self.pageID = uid
                    log.debug("Found Page %s:%s:%s" % (uid,scope,title))

            #Didnt find the page so create one
            if self.pageID is None:
                try:
                    self.pageID, title = self.ba.page.create(self.storeInPage)
                    log.info("Created page %s (id: %s)" % (title, self.pageID))
                except backpack.BackpackError, err:
                    log.info("Could not create page to store notes in (%s)" % err)
                    raise Exceptions.RefreshError
                    
        #Need to cache the existing note titles
        for uid, title, timestamp, text in self.ba.notes.list(self.pageID):
            self._notes[title] = uid
            log.debug("Found existing note: %s (%s)" % (title, uid))

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
        apikeyEntry.set_text(self.apikey)
        pagenameEntry.set_text(self.storeInPage)        
        
        dlg = tree.get_widget("BackpackNotesSinkConfigDialog")

        response = Utils.run_dialog(dlg, window)
        if response == True:
            self.username = usernameEntry.get_text()
            self.storeInPage = pagenameEntry.get_text()
            if apikeyEntry.get_text() != self.apikey:
                self.apikey = apikeyEntry.get_text()

            #user must enter their username
            if len(self.username) > 0 and len(self.apikey) > 0:
                self.set_configured(True)

        dlg.destroy()
        
    def get_all(self):
        return self._notes.values()
        
    def put(self, note, overwrite, LUID=None):
        DataProvider.DataSink.put(self, note, overwrite, LUID)

        #If all that went well then actually store some notes.
        uid = None
        try:
            if note.title in self._notes:
                log.debug("Updating Existing")
                uid = self._notes[note.title]
                self.ba.notes.update(self.pageID,uid,note.title,note.contents)
            else:
                log.debug("Creating New (title: %s)" % note.title)
                uid,title,mtime,content = self.ba.notes.create(self.pageID,note.title,note.contents)
                self._notes[note.title] = uid
        except backpack.BackpackError, err:
            log.info("Could not sync note (%s)" % err)
            raise Exceptions.SyncronizeError
                
        return Rid(uid=str(uid), mtime=None, hash=hash(None))

    def delete(self, LUID):
        if LUID in self._notes.values():
            try:
                self.ba.notes.destroy(self.pageID,LUID)
            except backpack.BackpackError, err:
                log.info("Could delete note (%s)" % err)
                raise Exceptions.SyncronizeError
        else:
            log.info("Could not find note")

    def get_UID(self):
        return "%s:%s" % (self.username,self.storeInPage)

    def set_configuration(self, config):
        DataProvider.DataSink.set_configuration(self, config)
        if len(self.username) > 0 and len(self.apikey) > 0:
            self.set_configured(True)

    def get_configuration(self):
        return {
            "username" : self.username,
            "apikey" : self.apikey,
            "storeInPage" : self.storeInPage
            }



