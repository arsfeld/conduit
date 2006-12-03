import os
import sys
import gtk
from gettext import gettext as _
import traceback

import logging
import conduit
import conduit.DataProvider as DataProvider
import conduit.Exceptions as Exceptions
import conduit.datatypes.Email as Email
import conduit.datatypes.Contact as Contact

try:
    import libgmail
    if libgmail.Version < "0.1.5.1":
        del(libgmail)
        logging.warn("Note: Using built in libgmail")
        sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"libgmail-0.1.5"))
        import libgmail
except ImportError:
    logging.warn("Note: Using built in libgmail")
    sys.path.append(os.path.join(conduit.EXTRA_LIB_DIR,"libgmail-0.1.5"))
    import libgmail


MODULES = {
	"GmailEmailSource" : {
		"name": _("Gmail Email Source"),
		"description": _("Sync your Gmail Emails"),
		"category": DataProvider.CATEGORY_GOOGLE,
		"type": "source",
		"in_type": "email",
		"out_type": "email"
	},
	"GmailEmailSink" : {
		"name": _("Gmail Email Sink"),
		"description": _("Sync your Gmail Emails"),
		"type": "sink",
		"category": DataProvider.CATEGORY_GOOGLE,
		"in_type": "email",
		"out_type": "email"
	},
	"GmailContactSource" : {
		"name": _("Gmail Contacts Source"),
		"description": _("Sync your Gmail Contacts"),
		"type": "source",
		"category": DataProvider.CATEGORY_GOOGLE,
		"in_type": "contact",
		"out_type": "contact"
	},
	"GmailContactSink" : {
		"name": _("Gmail Contacts Sink"),
		"description": _("Sync your Gmail Contacts"),
		"type": "sink",
		"category": DataProvider.CATEGORY_GOOGLE,
		"in_type": "vCard",
		"out_type": "vCard"
	},
	"EmailSinkConverter" : {
		"name": _("Email Sink Converter"),
		"description": _("I Concur"),
		"type": "converter",
		"category": "",
		"in_type": "",
		"out_type": "",
	}           
}

class GmailBase(DataProvider.DataProviderBase):
    """
    Simple wrapper to share gmail login stuff
    """
    def __init__(self):
        self.username = ""
        self.password = ""

        self.loggedIn = False
        self.ga = None
    
    def initialize(self):
        return True

    def refresh(self):
        try:
            self.ga = libgmail.GmailAccount(self.username, self.password)
            self.ga.login()
            self.loggedIn = True
        except:
            logging.warn("Error logging into gmail (username %s)\n%s" % (self.username,traceback.format_exc()))
            raise Exceptions.RefreshError
            
class GmailEmailSource(GmailBase, DataProvider.DataSource):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSource.__init__(self, _("Gmail Email Source"), _("Sync your Gmail Emails"), "internet-mail")
        
        #What emails should the source return??
        self.getAllEmail = False
        self.getUnreadEmail = False
        self.getWithLabel = ""
        self.getInFolder = ""
        self.mails = []
        
    def configure(self, window):
        """
        Configures the GmailSource for which emails it should return
        
        All the inner function foo is because the allEmail
        option is mutually exclusive with all the others (which may be
        mixed according to the users preferences
        """
        def invalidate_options():
            if allEmailsCb.get_active():
                unreadEmailsCb.set_active(False)
                labelEmailsCb.set_active(False)
                folderEmailsCb.set_active(False)
                            
        def all_emails_toggled(foo):
            invalidate_options()
        
        def other_option_toggled(button):
            if button.get_active():
                allEmailsCb.set_active(False)
                invalidate_options()
            
        tree = gtk.glade.XML(conduit.GLADE_FILE, "GmailSourceConfigDialog")
        dic = { "on_allEmails_toggled" : all_emails_toggled,
                "on_unreadEmails_toggled" : other_option_toggled,
                "on_labelEmails_toggled" : other_option_toggled,
                "on_folderEmails_toggled" : other_option_toggled,
                None : None
                }
        tree.signal_autoconnect(dic)
        
        #get a whole bunch of widgets
        allEmailsCb = tree.get_widget("allEmails")
        unreadEmailsCb = tree.get_widget("unreadEmails")
        labelEmailsCb = tree.get_widget("labelEmails")
        folderEmailsCb = tree.get_widget("folderEmails")
        labelEntry = tree.get_widget("labels")
        usernameEntry = tree.get_widget("username")
        passwordEntry = tree.get_widget("password")
        
        #preload the widgets
        allEmailsCb.set_active(self.getAllEmail)
        unreadEmailsCb.set_active(self.getUnreadEmail)
        if (self.getWithLabel is not None) and (len(self.getWithLabel) > 0):
            labelEmailsCb.set_active(True)
            labelEntry.set_text(self.getWithLabel)
        else:
            labelEmailsCb.set_active(False)
        if (self.getInFolder is not None) and (len(self.getInFolder) > 0):
            folderEmailsCb.set_active(True)
        else:        
            folderEmailsCb.set_active(False)
        usernameEntry.set_text(self.username)
        
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
        tree.get_widget("propbox").pack_end(folderComboBox)
        
        dlg = tree.get_widget("GmailSourceConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            if allEmailsCb.get_active():
                self.getAllEmail = True
                self.getUnreadEmail = False
                self.getWithLabel = ""
                self.getInFolder = ""
            else:
                self.getAllEmail = False
                self.getUnreadEmail = unreadEmailsCb.get_active()
                self.getWithLabel = labelEntry.get_text()
                self.getInFolder = folderComboBox.get_active_text()
            self.username = usernameEntry.get_text()
            if passwordEntry.get_text() != self.password:
                self.password = passwordEntry.get_text()
        dlg.destroy()    

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        GmailBase.refresh(self)

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
        DataProvider.DataSource.get(self, index)
        return self.mails[index]

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.mails)

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            "getAllEmals" : self.getAllEmail,
            "getUnreadEmail" : self.getUnreadEmail,
            "getWithLabel" : self.getWithLabel,
            "getInFolder" : self.getInFolder
            }            


class GmailEmailSink(GmailBase, DataProvider.DataSink):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSink.__init__(self, _("Gmail Email Sink"), _("Sync your Gmail Emails"), "internet-mail")
        
        self.label = "Conduit"
        
    def configure(self, window):
        """
        Configures the GmailSource for which emails it should return
        
        All the inner function foo is because the allEmail
        option is mutually exclusive with all the others (which may be
        mixed according to the users preferences
        """
        tree = gtk.glade.XML(conduit.GLADE_FILE, "GmailSinkConfigDialog")
        
        #get a whole bunch of widgets
        labelEmailsCb = tree.get_widget("labelEmails")
        labelEntry = tree.get_widget("labels")
        usernameEntry = tree.get_widget("username")
        passwordEntry = tree.get_widget("password")
        
        #preload the widgets
        labelEmailsCb.set_active(len(self.label) > 0)
        labelEntry.set_text(self.label)
        usernameEntry.set_text(self.username)
        
        dlg = tree.get_widget("GmailSinkConfigDialog")
        dlg.set_transient_for(window)
        
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            if labelEmailsCb.get_active():
                self.label = labelEntry.get_text()
            self.username = usernameEntry.get_text()
            if passwordEntry.get_text() != self.password:
                self.password = passwordEntry.get_text()
        dlg.destroy()    
        
    def put(self, email, emailOnTopOf=None):
        DataProvider.DataSink.put(self, email, emailOnTopOf)

        if email.has_attachments():
            attach = email.attachments
        else:
            attach = None
        
        msg = libgmail.GmailComposedMessage(
                                to="", 
                                subject=email.subject, 
                                body=email.content,
                                filenames=attach)

        draftMsg = self.ga.sendMessage(msg, asDraft = True)

        if draftMsg and self.label:
            try:
                draftMsg.addLabel(self.label)
            except Exception, err:
                logging.warn("Error adding label to message: %s\n%s" % (err,traceback.format_exc()))

    def get_configuration(self):
        return {
            "username" : self.username,
            "password" : self.password,
            "label" : self.label
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
        

class GmailContactSource(GmailBase, DataProvider.DataSource):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSource.__init__(self, _("Gmail Contacts Source"), _("Sync your Gmail Contacts"), "contact-new")
        self.contacts = []
        self.username = ""
        self.password = ""

    def initialize(self):
        return True

    def refresh(self):
        DataProvider.DataSource.refresh(self)
        GmailBase.refresh(self)

        if self.loggedIn:
            result = self.ga.getContacts().getAllContacts()
            self.contacts = []
            for c in result:
                #FIXME: When Contact can load a vcard file, use that instead!
               contact = Contact.Contact()
               contact.readVCard(c.getVCard())
               self.contacts.append(contact)
        else:
            raise Exceptions.SyncronizeFatalError

    def get_num_items(self):
        DataProvider.DataSource.get_num_items(self)
        return len(self.contacts)

    def get(self, index):
        DataProvider.DataSource.get(self, index)
        return self.contacts[index]

    def configure(self, window):
        tree = gtk.glade.XML(conduit.GLADE_FILE, "GmailSinkConfigDialog")
        
        #get a whole bunch of widgets
        labelEmailsCb = tree.get_widget("labelEmails")
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

class GmailContactSink(GmailBase, DataProvider.DataSink):
    def __init__(self):
        GmailBase.__init__(self)
        DataProvider.DataSink.__init__(self, _("Gmail Contacts Sink"), _("Sync your Gmail Contacts"), "contact-new")

    def initialize(self):
        return False

    def refresh(self):
        DataProvider.DataSink.refresh(self)
        GmailBase.refresh(self)

    def put(self, contact, contactOnTopOf):
        DataProvider.DataSink.put(self, contact, contactOnTopOf)
