import os
import sys
import gtk
from gettext import gettext as _
import traceback

import logging
import conduit
import conduit.Utils as Utils
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Email as Email
import conduit.datatypes.Contact as Contact

Utils.dataprovider_add_dir_to_path(__file__, "libgmail-0.1.5")
import libgmail

MODULES = {
	"GmailEmailTwoWay" :    { "type": "dataprovider" },
	"GmailContactTwoWay" :  { "type": "dataprovider" },
	"EmailSinkConverter" :  { "type": "converter" }
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
            try:
                self.ga = libgmail.GmailAccount(self.username, self.password)
                self.ga.login()
                self.loggedIn = True
            except:
                logging.warn("Error logging into gmail (username %s)\n%s" % (self.username,traceback.format_exc()))
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
    _in_type = "email"
    _out_type = "email"
    _icon_ = "internet-mail"

    def __init__(self, *args):
        GmailBase.__init__(self, *args)
        DataProvider.TwoWay.__init__(self)
        
        #What emails should the source return??
        self.getAllEmail = False
        self.getUnreadEmail = False
        self.getWithLabel = ""
        self.getInFolder = ""
        self.mails = None
        
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
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
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

        self.mails = []

        if self.loggedIn:
            if self.getAllEmail:
                logging.debug("Getting all Email")
                pass
            else:
                if self.getUnreadEmail:
                    logging.debug("Getting Unread Email")                
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
                                mail = Email.Email()
                                mail.create_from_raw_source(message.source)
                                self.mails.append(mail)                    
                elif len(self.getWithLabel) > 0:
                    logging.debug("Getting Email Labelled: %s" % self.getWithLabel)                
                    result = self.ga.getMessagesByLabel(self.getWithLabel)
                    if len(result):
                        for thread in result:
                            for message in thread:
                                mail = Email.Email()
                                mail.create_from_raw_source(message.source)
                                self.mails.append(mail)
                elif len(self.getInFolder) > 0:
                    logging.debug("Getting Email in Folder: %s" % self.getInFolder)                
                    result = self.ga.getMessagesByFolder(self.getInFolder)
                    if len(result):
                        for thread in result:
                            for message in thread:
                                mail = Email.Email()
                                mail.create_from_raw_source(message.source)
                                self.mails.append(mail)
        else:
            raise Exceptions.SyncronizeFatalError
                
    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        return self.mails[index]

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.mails)

    def put(self, email, overwrite, LUIDs=[]):
        DataProvider.TwoWay.put(self, email, overwrite, LUIDs)

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
        except libgmail.GmailSendError:
            raise Exceptions.SyncronizeError("Error saving message")

        if draftMsg and self.label:
            try:
                draftMsg.addLabel(self.label)
            except Exception, err:
                logging.warn("Error adding label to message: %s\n%s" % (err,traceback.format_exc()))

        return draftMsg.id

    def finish(self):
        self.mails = None

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            "getAllEmals" : self.getAllEmail,
            "getUnreadEmail" : self.getUnreadEmail,
            "getWithLabel" : self.getWithLabel,
            "getInFolder" : self.getInFolder
            }            
        
class EmailSinkConverter:

    def __init__(self):
        self.conversions =  {    
                            "file,email" : self.file_to_email,
                            "text,email" : self.text_to_email
                            }
                            
                            
    def file_to_email(self, thefile):
        """
        If the file is non binary then include it as the
        Subject of the message. Otherwise include it as an attachment
        """
        mimeCategory = thefile.get_mimetype().split('/')[0]
        if mimeCategory == "text":
            #insert the contents into the email
            logging.debug("Inserting file contents into email")
            email = Email.Email()
            email.create(   "",                             #to
                            "",                             #from
                            thefile.get_filename(),         #subject
                            thefile.get_contents_as_text()  #contents
                            )
            return email
        else:
            #binary file so send as attachment
            logging.debug("Binary file, attaching to email")
            email = Email.Email()
            email.create(   "",                             #to
                            "",                             #from
                            thefile.get_filename(),         #subject
                            "Attached"                      #contents
                            )
            email.add_attachment(thefile.get_local_uri())
            return email
            
    def text_to_email(self, text):
        email = Email.Email()
        email.create(   "",                             #to
                        "",                             #from
                        "",                             #subject
                        text                            #contents
                        )
        return email
        

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
        self.contacts = None
        self.username = ""
        self.password = ""

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.TwoWay.refresh(self)
        GmailBase.refresh(self)

        self.contacts = []

        if self.loggedIn:
            result = self.ga.getContacts().getAllContacts()
            for c in result:
                #FIXME: When Contact can load a vcard file, use that instead!
               contact = Contact.Contact()
               contact.readVCard(c.getVCard())
               self.contacts.append(contact)
        else:
            raise Exceptions.SyncronizeFatalError

    def get_num_items(self):
        DataProvider.TwoWay.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        DataProvider.TwoWay.get(self, index)
        return self.contacts[index]

    def put(self, contact, overwrite, LUIDs=[]):
        DataProvider.TwoWay.put(self, contact, overwrite, LUIDs)

    def finish(self):
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
        dlg.destroy()

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            }