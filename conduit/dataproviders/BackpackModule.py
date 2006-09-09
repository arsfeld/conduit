import os
import sys
import traceback
import gtk
from gettext import gettext as _

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Note as Note

try:
    import backpack
except ImportError:
    logging.warn("Note: Using built in backpack")
    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"backpack-1.1"))
    import backpack


MODULES = {
	"BackpackNoteSink" : {
		"name": _("Backpack Note Sink"),
		"description": _("Store things in Backpack Notes"),
		"category": DataProvider.CATEGORY_WEB,
		"type": "sink",
		"in_type": "note",
		"out_type": "note"
	}          
}

class BackpackBase(DataProvider.DataProviderBase):
    """
    Simple wrapper to share gmail login stuff
    """
    def __init__(self):
        self.username = ""
        self.apikey = ""

        self.ba = None
    
    def refresh(self):
        username = "http://" + self.username + ".backpackit.com/"
        try:
            self.ba = backpack.Backpack(username,self.apikey)
            self.loggedIn = True
        except backpack.BackpackError:
            logging.warn("Error logging into backpack (username %s)" % self.username)
            raise Exceptions.RefreshError
    

class BackpackNoteSink(BackpackBase, DataProvider.DataSink):
    def __init__(self):
        BackpackBase.__init__(self)
        DataProvider.DataSink.__init__(self, _("Backpack Note Sink"), _("Store things in Backpack Notes"))
        self.icon_name = "backpack"
        
        self.storeInPage = "Conduit"
        self.pageID = None
        self.existingNotes = {}
        
    def configure(self, window):
        tree = gtk.glade.XML(conduit.GLADE_FILE, "BackpackNotesSinkConfigDialog")
        
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
        
        
    def put(self, note, noteOnTopOf=None):
        #First search for the pageID of the named page to put notes in
        if self.pageID is None:
            pages = self.ba.page.list()
            for uid,scope,title in pages:
                if title == self.storeInPage:
                    self.pageID = uid
                    logging.debug("Found Page %s:%s:%s" % (uid,scope,title))
            #Didnt find the page so create
            if self.pageID is None:
                try:
                    self.pageID, foo = self.ba.page.create(self.storeInPage,"Automatically Synchronized Notes")
                    logging.info("Created page")
                except backpack.BackpackError, err:
                    logging.info("Could not create page to store notes in (%s)" % err)
                    #cannot continue
                    raise SyncronizeFatalError
                    
        #Now check if any notes we want to store are already there and need 
        #updating
        if len(self.existingNotes) == 0:
            notes = self.ba.notes.list(self.pageID)
            for uid, title, timestamp, text in notes:
                self.existingNotes[title] = uid
            logging.debug("Found existing notes: %s" % self.existingNotes)
        
        #If all that went well then actually store some notes.
        try:
            if note.title in self.existingNotes:
                logging.debug("Updating Existing")
                self.ba.notes.update(self.pageID,self.existingNotes[note.title],note.title,note.contents)
            else:
                logging.debug("Creating New")
                self.ba.notes.create(self.pageID,note.title,note.contents)
        except backpack.BackpackError, err:
            logging.info("Could not sync note (%s)" % err)
            raise SyncronizeError
                
    def get_configuration(self):
        return {
            "storeInPage" : self.storeInPage,
            "username" : self.username,
            "apikey" : self.apikey
            }
