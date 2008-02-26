from gettext import gettext as _
import traceback
import logging
log = logging.getLogger("modules.Gmail")

import conduit
import conduit.Utils as Utils
import conduit.dataproviders.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
from conduit.datatypes import Rid
import conduit.datatypes.Email as Email
import conduit.datatypes.Contact as Contact

#Distributors, we pretty much ship the most recent libgmail CVS because
#its not supported by google, so tends to break often
Utils.dataprovider_add_dir_to_path(__file__, "libgmail")
import libgmail
import lgconstants

MODULES = {
    "GmailEmailTwoWay" :    { "type": "dataprovider" },
    "GmailContactSource" :  { "type": "dataprovider" },
}

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

    def is_configured (self, isSource, isTwoWay):
        if len(self.username) < 1:
            return False
        if len(self.password) < 1:
            return False
        return True

    def refresh(self):
        if self.loggedIn == False:
            if "@" in self.username:
                user, domain = self.username.split("@")
                #FIXME: Libgmail dies if the specified domain is just a gmail one
                if domain in ("gmail.com", "googlemail.com"):
                    domain = None
            else:
                user = self.username
                domain = None

            try:
                self.ga = libgmail.GmailAccount(user, self.password, domain=domain)
                self.ga.login()
                self.loggedIn = True
            except:
                log.warn("Error logging into gmail (username %s)\n%s" % (self.username,traceback.format_exc()))
                raise Exceptions.RefreshError

    def get_UID(self):
        return self.username

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            }

class GmailEmailTwoWay(GmailBase, DataProvider.TwoWay):

    _name_ = _("Gmail Emails")
    _description_ = _("Sync your emails")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "twoway"
    _in_type_ = "email"
    _out_type_ = "email"
    _icon_ = "emblem-mail"

    def __init__(self, *args):
        GmailBase.__init__(self, *args)
        DataProvider.TwoWay.__init__(self)

        #What emails should the source return??
        self.saveWithLabel = "Conduit-%s" % conduit.VERSION
        self.getAllEmail = False
        self.getUnreadEmail = False
        self.getWithLabel = ""
        self.getInFolder = ""
        self.mails = {}
        
    def configure(self, window):
        """
        Configures the GmailSource for which emails it should return
        
        All the inner function foo is because the allEmail
        option is mutually exclusive with all the others (which may be
        mixed according to the users preferences
        """
        import gtk
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
        saveLabelEntry = tree.get_widget("saveLabel")
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
        passwordEntry.set_text(self.password)
        saveLabelEntry.set_text(self.saveWithLabel)
        
        dlg = tree.get_widget("GmailSourceConfigDialog")
        
        response = Utils.run_dialog (dlg, window)
        if response == True:
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
        self.saveWithLabel = saveLabelEntry.get_text()
        dlg.destroy()

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        GmailBase.refresh(self)

        self.mails = {}

        if self.loggedIn:
            result = []
            if self.getAllEmail:
                log.debug("Getting all Email")
                result = self.ga.getMessagesByFolder(lgconstants.U_INBOX_SEARCH)
            else:
                if self.getUnreadEmail:
                    log.debug("Getting Unread Email")                
                    result = self.ga.getUnreadMessages()
                elif self.getWithLabel != None and len(self.getWithLabel) > 0:
                    log.debug("Getting Email Labelled: %s" % self.getWithLabel)                
                    result = self.ga.getMessagesByLabel(self.getWithLabel)
                elif self.getInFolder != None and len(self.getInFolder) > 0:
                    log.debug("Getting Email in Folder: %s" % self.getInFolder)                
                    result = self.ga.getMessagesByFolder(self.getInFolder)
                else:
                    log.debug("Not getting any email")

            if len(result):                    
                for thread in result:
                    for message in thread:
                        mail = Email.Email()
                        mail.set_from_email_string(message.source)
                        self.mails[message.id] = mail                          

        else:
            raise Exceptions.SyncronizeFatalError("Not logged in")
                
    def get(self, LUID):
        DataProvider.TwoWay.get(self, LUID)
        mail = self.mails.get(LUID)
        if mail == None:
            mail = Email.Email()
            mail.set_from_email_string(
                    self.ga.getRawMessage(LUID)
                    )
        return mail

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
                                subject=email.get_subject(), 
                                body="",
                                filenames=attach)

        try:
            draftMsg = self.ga.sendMessage(msg, asDraft=True)
            draftMsg.addLabel(self.saveWithLabel)
        except libgmail.GmailSendError:
            raise Exceptions.SyncronizeError("Error saving message")
        except Exception, err:
            traceback.print_exc()
            raise Exceptions.SyncronizeError("Error adding label %s to message" % self.saveWithLabel)
            
        return Rid(uid=draftMsg.id)

    def finish(self, aborted, error, conflict):
        DataProvider.TwoWay.finish(self)
        self.mails = None

    def get_configuration(self):
        conf = GmailBase.get_configuration(self)
        conf.update({
                "getAllEmail" : self.getAllEmail,
                "getUnreadEmail" : self.getUnreadEmail,
                "getWithLabel" : self.getWithLabel,
                "getInFolder" : self.getInFolder,
                "saveWithLabel" : self.saveWithLabel})
        return conf

class GmailContactSource(GmailBase, DataProvider.DataSource):

    _name_ = _("Gmail Contacts")
    _description_ = _("Sync your contacts")
    _category_ = conduit.dataproviders.CATEGORY_OFFICE
    _module_type_ = "source"
    _in_type_ = "contact"
    _out_type_ = "contact"
    _icon_ = "contact-new"
    
    VCARD_EXPORT_URI = "http://mail.google.com/mail/contacts/data/export?exportType=ALL&groupToExport=&out=VCARD"

    def __init__(self, *args):
        GmailBase.__init__(self, *args)
        DataProvider.DataSource.__init__(self)
        self.contacts = {}

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        GmailBase.refresh(self)
        
        self.contacts = {}
        if self.loggedIn:
            log.debug("Getting all contacts as vcards")
            pageData = self.ga._retrievePage(GmailContactSource.VCARD_EXPORT_URI)
            for c in Contact.parse_vcf(pageData):
                self.contacts[c.get_emails()[0]] = c
            #FIXME: Libgmail is not really reliable....
            #result = self.ga.getContacts().getAllContacts()
            #for c in result:
            #   contact = Contact.Contact()
            #   contact.set_from_vcard_string(c.getVCard())
            #   self.contacts[c.get_emails()[0]] = contact
        else:
            raise Exceptions.SyncronizeFatalError

    def get_all(self):
        DataProvider.DataSource.get_all(self)
        return self.contacts.keys()

    def get(self, LUID):
        DataProvider.DataSource.get(self, LUID)
        c = self.contacts[LUID]
        c.set_UID(LUID)
        return c

    def finish(self, aborted, error, conflict):
        DataProvider.DataSource.finish(self)
        self.contacts = {}

    def configure(self, window):
        tree = Utils.dataprovider_glade_get_widget(
                        __file__, 
                        "config.glade",
                        "GmailContactSourceConfigDialog")
        usernameEntry = tree.get_widget("username2")
        passwordEntry = tree.get_widget("password2")
        usernameEntry.set_text(self.username)
        passwordEntry.set_text(self.password)
        
        dlg = tree.get_widget("GmailContactSourceConfigDialog")
        response = Utils.run_dialog (dlg, window)
        if response == True:
            self.username = usernameEntry.get_text()
            if passwordEntry.get_text() != self.password:
                self.password = passwordEntry.get_text()
        dlg.destroy()

