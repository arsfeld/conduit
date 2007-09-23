import os
import sys
import gtk
from gettext import gettext as _
import traceback


import conduit
from conduit import log,logd,logw
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Email as Email
import conduit.datatypes.Contact as Contact

Utils.dataprovider_add_dir_to_path(__file__, "libgmail-0.1.6.2")
import libgmail

MODULES = {
    "GmailEmailTwoWay" :    { "type": "dataprovider" },
#    "GmailContactTwoWay" :  { "type": "dataprovider" },
}

GOOGLE_CAT = DataProvider.DataProviderCategory("Google", "applications-internet")

class GmailBase(DataProvider.DataProviderBase):
    """
    Simple wrapper to share gmail login stuff
    """
    def __init__(self, *args):
        self.username = ""
        self.password = ""

        self.loggedIn = False
        self.ga = None
    
    def initialize(self):
        return True

    def refresh(self):
        if self.loggedIn == False:
            if "@" in self.username:
                user, domain = self.username.split("@")
            else:
                user = self.username
                domain = None

            try:
                self.ga = libgmail.GmailAccount(user, self.password, domain=domain)
                self.ga.login()
                self.loggedIn = True
            except:
                logw("Error logging into gmail (username %s)\n%s" % (self.username,traceback.format_exc()))
                raise Exceptions.RefreshError

    def get_UID(self):
        return self.username

    def _message_exists(self, msgid):
        """
        Utility function to check if a message exists. Does so by searching
        the raw message contents for certain seemingly compulsory strings;
        (taken from RFC 822)
            1)  Received
            2)  Date
            4)  Subject
        I do it this way because if the message is not found then gmail returns
        a help message that may change in future. RFC822 wont change.
        """
        raw = self.ga.getRawMessage(msgid)
        try:
            raw.index("Received")
            raw.index("Date")
            raw.index("Subject")
            return True
        except ValueError:
            return False
            
class GmailEmailTwoWay(GmailBase, DataProvider.TwoWay):

    _name_ = _("Email")
    _description_ = _("Sync your Gmail Emails")
    _category_ = GOOGLE_CAT
    _module_type_ = "twoway"
    _in_type_ = "email"
    _out_type_ = "email"
    _icon_ = "emblem-mail"

    def __init__(self, *args):
        GmailBase.__init__(self, *args)
        DataProvider.TwoWay.__init__(self)
        self.need_configuration(True)
        
        #What emails should the source return??
        self.getAllEmail = False
        self.getUnreadEmail = False
        self.getWithLabel = ""
        self.getInFolder = ""
        self.mails = None

        #For bookkeeping 
        self._label = "%s-%s" % (conduit.APPNAME,conduit.APPVERSION)
        
    def configure(self, window):
        """
        Configures the GmailSource for which emails it should return
        
        All the inner function foo is because the allEmail
        option is mutually exclusive with all the others (which may be
        mixed according to the users preferences
        """
        def invalidate_options():
            if searchAllEmailsCb.get_active():
                searchUnreadEmailsCb.set_active(False)
                searchLabelEmailsCb.set_active(False)
                searchFolderEmailsCb.set_active(False)
                labelEntry.set_sensitive(False)
                folderComboBox.set_sensitive(False)
                            
        def all_emails_toggled(foo):
            invalidate_options()
        
        def other_option_toggled(button):
            if button == searchLabelEmailsCb:
                labelEntry.set_sensitive(button.get_active())
            if button == searchFolderEmailsCb:
                folderComboBox.set_sensitive(button.get_active())
            if button.get_active():
                searchAllEmailsCb.set_active(False)
                invalidate_options()
            
            
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "GmailSourceConfigDialog")

        dic = { "on_searchAllEmails_toggled" : all_emails_toggled,
                "on_searchUnreadEmails_toggled" : other_option_toggled,
                "on_searchLabelEmails_toggled" : other_option_toggled,
                "on_searchFolderEmails_toggled" : other_option_toggled,
                None : None
                }
        tree.signal_autoconnect(dic)

        #Add and fill a combo box with the Gmail Folders
        index = 0
        folderComboBox = gtk.combo_box_new_text()
        for folder in libgmail.STANDARD_FOLDERS:
            folderComboBox.insert_text(index,folder)
            #Check if it should be selected already
            if folder == self.getInFolder:
                folderComboBox.set_active(index)    
            index += 1
        folderComboBox.show()
        tree.get_widget("folderBox").pack_end(folderComboBox)
        
        #get a whole bunch of widgets
        searchAllEmailsCb = tree.get_widget("searchAllEmails")
        searchUnreadEmailsCb = tree.get_widget("searchUnreadEmails")
        searchLabelEmailsCb = tree.get_widget("searchLabelEmails")
        searchFolderEmailsCb = tree.get_widget("searchFolderEmails")
        labelEntry = tree.get_widget("labels")
        usernameEntry = tree.get_widget("username")
        passwordEntry = tree.get_widget("password")
        
        #preload the widgets
        searchAllEmailsCb.set_active(self.getAllEmail)
        searchUnreadEmailsCb.set_active(self.getUnreadEmail)
        if (self.getWithLabel is not None) and (len(self.getWithLabel) > 0):
            searchLabelEmailsCb.set_active(True)
            labelEntry.set_text(self.getWithLabel)
            labelEntry.set_sensitive(True)
        else:
            searchLabelEmailsCb.set_active(False)
            labelEntry.set_sensitive(False)
        if (self.getInFolder is not None) and (len(self.getInFolder) > 0):
            searchFolderEmailsCb.set_active(True)
        else:        
            searchFolderEmailsCb.set_active(False)
            folderComboBox.set_sensitive(False)
        usernameEntry.set_text(self.username)
        
        dlg = tree.get_widget("GmailSourceConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == gtk.RESPONSE_OK:
            self.set_configured(True)
            if searchAllEmailsCb.get_active():
                self.getAllEmail = True
                self.getUnreadEmail = False
                self.getWithLabel = ""
                self.getInFolder = ""
            else:
                self.getAllEmail = False
                self.getUnreadEmail = searchUnreadEmailsCb.get_active()
                if searchLabelEmailsCb.get_active():
                    self.getWithLabel = labelEntry.get_text()
                else:
                    self.getWithLabel = ""
                self.getInFolder = folderComboBox.get_active_text()

            self.username = usernameEntry.get_text()
            if passwordEntry.get_text() != self.password:
                self.password = passwordEntry.get_text()
        dlg.destroy()

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        GmailBase.refresh(self)

        self.mails = {}

        if self.loggedIn:
            if self.getAllEmail:
                logd("Getting all Email")
                pass
            else:
                if self.getUnreadEmail:
                    logd("Getting Unread Email")                
                    #FIXME: These TODO notes taken from libgmail examples
                    #Check if these TODOs have been answered at a future
                    #date
                    # TODO: Work out at what stage messages get marked as 'read'.
                    #       (as I think of it, it happens when I retrieve the
                    #        messages in the threads, should really preserve read/unread
                    #        state then.)
                    # TODO: Fix this so it does not retrieve messages that have already
                    #       been read. ("unread" is a property of thread in this case?)
                    #       Is this even possible without caching stuff ourselves,
                    #       maybe use "archive" as the equivalent of read?
                    result = self.ga.getUnreadMessages()
                    if len(result):                    
                        for thread in result:
                            for message in thread:
                                mail = Email.Email(None)
                                mail.set_from_email_string(message.source)
                                self.mails[message.id] = mail              
                elif len(self.getWithLabel) > 0:
                    logd("Getting Email Labelled: %s" % self.getWithLabel)                
                    result = self.ga.getMessagesByLabel(self.getWithLabel)
                    if len(result):
                        for thread in result:
                            for message in thread:
                                mail = Email.Email(None)
                                mail.set_from_email_string(message.source)
                                self.mails[message.id] = mail
                elif len(self.getInFolder) > 0:
                    logd("Getting Email in Folder: %s" % self.getInFolder)                
                    result = self.ga.getMessagesByFolder(self.getInFolder)
                    if len(result):
                        for thread in result:
                            for message in thread:
                                mail = Email.Email(None)
                                mail.set_from_email_string(message.source)
                                self.mails[message.id] = mail
        else:
            raise Exceptions.SyncronizeFatalError
                
    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self.mails[LUID]

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return [x for x in self.mails.iterkeys()]

    def put(self, email, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, email, overwrite, LUID)

        if email.has_attachments():
            attach = email.attachments
        else:
            attach = None
        
        msg = libgmail.GmailComposedMessage(
                                to="", 
                                subject=email.subject, 
                                body=email.content,
                                filenames=attach)

        try:
            draftMsg = self.ga.sendMessage(msg, asDraft = True)
            draftMsg.addLabel(self._label)
        except libgmail.GmailSendError:
            raise Exceptions.SyncronizeError("Error saving message")
        except Exception, err:
            raise Exceptions.SyncronizeError("Error adding label %s to message" % self._label)

        return draftMsg.id

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.mails = None

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            "getAllEmail" : self.getAllEmail,
            "getUnreadEmail" : self.getUnreadEmail,
            "getWithLabel" : self.getWithLabel,
            "getInFolder" : self.getInFolder
            }            
        
     
class GmailContactTwoWay(GmailBase, DataProvider.TwoWay):

    _name_ = _("Contacts")
    _description_ = _("Sync your Gmail Contacts")
    _category_ = GOOGLE_CAT
    _module_type_ = "twoway"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"

    def __init__(self, *args):
        GmailBase.__init__(self, *args)
        DataProvider.TwoWay.__init__(self)
        self.need_configuration(True)

        self.contacts = None
        self.username = ""
        self.password = ""

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        GmailBase.refresh(self)

        self.contacts = {}

        if self.loggedIn:
            result = self.ga.getContacts().getAllContacts()
            for c in result:
                #FIXME: When Contact can load a vcard file, use that instead!
               contact = Contact.Contact()
               contact.set_from_vcard_string(c.getVCard())
               contact.set_UID(c.email)
               self.contacts[c.email] = contact
        else:
            raise Exceptions.SyncronizeFatalError

    def get_all(self):
        DataProvider.TwoWay.get_all(self)
        return [x for x in self.contacts.iterkeys()]

    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        return self.contacts[LUID]

    def put(self, contact, overwrite, LUID=None):
        DataProvider.TwoWay.put(self, contact, overwrite, LUID)

    def finish(self):
        DataProvider.TwoWay.finish(self)
        self.contacts = None

    def configure(self, window):
        tree = gtk.glade.XML(conduit.GLADE_FILE, "GmailSinkConfigDialog")
        
        #get a whole bunch of widgets
        searchLabelEmailsCb = tree.get_widget("searchLabelEmails")
        labelEntry = tree.get_widget("labels")
        usernameEntry = tree.get_widget("username")
        passwordEntry = tree.get_widget("password")
        
        #preload the widgets
        usernameEntry.set_text(self.username)
        
        dlg = tree.get_widget("GmailSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            self.username = usernameEntry.get_text()
            if passwordEntry.get_text() != self.password:
                self.password = passwordEntry.get_text()
                self.set_configured(True)
        dlg.destroy()

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            }

