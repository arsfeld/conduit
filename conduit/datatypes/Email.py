import logging
import conduit
from conduit.datatypes import DataType

import email

class Email(DataType.DataType):
    """
    Basic email representation
    """
    def __init__(self):
        DataType.DataType.__init__(self,"email")

        self.email = None
        self.to = ""
        self.emailFrom = ""
        self.subject = ""
        self.content = ""   
        self.attachments = []          
        
    def create(self, to, emailFrom, subject, content):
        self.to = to
        self.emailFrom = emailFrom
        self.subject = subject
        self.content = content                 
        
    def has_attachments(self):
        if len(self.attachments) > 0:
            return True
        return False
        
    def add_attachment(self, attachmentLocalPath):
        self.attachments.append(attachmentLocalPath)

    def create_from_raw_source(self, text_source):
        """
        Uses pythons built in email parsing thingamajig to parse
        the email emailFrom the raw string representation following
        all the emaily RFC standards and doing stuff that I have no idea
        about
        
        @todo: Actually read the python docs on how this works
        """
        self.email = email.message_from_string(text_source)
        
        if self.email is not None:
            if self.email.is_multipart():
                self.content = self.email.get_payload(0)
            else:
                self.content = self.email.get_payload()
                
            try:
                self.to = self.email['to']
                self.emailFrom = self.email['from']
                self.subject = self.email['subject']                
            except:
                logging.warn("Error parsing email message")

    def __str__(self):
        return ("To: %s\nFrom: %s\nSubject: %s\nMsg:\n%s" % (self.to,self.emailFrom,self.subject,self.content))
