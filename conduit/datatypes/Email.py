import email 
import logging
log = logging.getLogger("dataproviders.Email")


import conduit
from conduit.datatypes import DataType

class Email(DataType.DataType):
    """
    Basic email representation
    """

    _name_ = "email"

    def __init__(self, URI, **kwargs):
        DataType.DataType.__init__(self)

        self.raw = ""
        self.email = None
        self.attachments = []

        self.to = kwargs.get("to", "")
        self.emailFrom = kwargs.get("from", "")
        self.subject = kwargs.get("subject", "")
        self.content = kwargs.get("content", "")

        self.set_open_URI(URI)
        
    def has_attachments(self):
        if len(self.attachments) > 0:
            return True
        return False
        
    def add_attachment(self, attachmentLocalPath):
        self.attachments.append(attachmentLocalPath)

    def set_from_email_string(self, text_source):
        """
        Uses pythons built in email parsing thingamajig to parse
        the email emailFrom the raw string representation following
        all the emaily RFC standards and doing stuff that I have no idea
        about
        
        @todo: Actually read the python docs on how this works
        """
        self.email = email.message_from_string(text_source)
        
        if self.email is not None:
            self.raw = text_source

            if self.email.is_multipart():
                self.content = self.email.get_payload(0)
            else:
                self.content = self.email.get_payload()
                
            try:
                self.to = self.email['to']
                self.emailFrom = self.email['from']
                self.subject = self.email['subject']                
            except:
                log.warn("Error parsing email message")

    def get_email_string(self):
        #FIXME: make a self.email and use pythons methods to get the raw string
        raise NotImplementedError

    def __str__(self):
        return ("To: %s\nFrom: %s\nSubject: %s\n" % (self.to,self.emailFrom,self.subject))
        
    def get_hash(self):
        return hash( (self.to,self.emailFrom,self.subject,self.content) )
        
