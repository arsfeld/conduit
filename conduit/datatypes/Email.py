import email
from email import Encoders
from email.MIMEAudio import MIMEAudio
from email.MIMEBase import MIMEBase
from email.MIMEMultipart import MIMEMultipart
from email.MIMEImage import MIMEImage
from email.MIMEText import MIMEText

import logging
log = logging.getLogger("dataproviders.Email")

import conduit
from conduit.datatypes import DataType, File

class Email(DataType.DataType):
    """
    Basic email representation.
    Based on: http://aspn.activestate.com/ASPN/docs/ActivePython/2.4/python/lib/node597.html
    """
    _name_ = "email"
    def __init__(self, **kwargs):
        DataType.DataType.__init__(self)
        self.attachments = []

        self.email = MIMEText(kwargs.get("content", ""))
        self.email['Subject'] = kwargs.get("subject", "")
        self.email['To'] = kwargs.get("to", "")
        self.email['From'] = kwargs.get("from", "")
        self.email.preamble = ''
        self.email.epilogue = ''

    def has_attachments(self):
        if len(self.attachments) > 0:
            return True
        return False
        
    def add_attachment(self, path):
        #Create a multipart message and each attachment gets a part
        if not self.email.is_multipart():
            newemail = MIMEMultipart()
            newemail['Subject'] = self.email['Subject']
            newemail['To'] = self.email['To']
            newemail['From'] = self.email['From']
            newemail.preamble = 'There are attachments\n'
            newemail.epilogue = ''
            self.email = newemail

        f = File.File(path)
        filename = f.get_filename()
        mt = f.get_mimetype()
        maintype, subtype = mt.split('/', 1)
        if maintype == 'text':
            fp = open(path)
            #We should handle calculating the charset
            msg = MIMEText(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = open(path, 'rb')
            msg = MIMEImage(fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = open(path, 'rb')
            msg = MIMEAudio(fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(path, 'rb')
            msg = MIMEBase('application', 'octet-stream')
            msg.set_payload(fp.read())
            fp.close()
            # Encode the payload using Base64
            Encoders.encode_base64(msg)
        # Set the filename parameter
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        self.email.attach(msg)
        self.attachments.append(path)

    def set_from_email_string(self, text_source):
        self.email = email.message_from_string(text_source)

    def get_email_string(self):
        return self.email.as_string()
    
    def get_subject(self):        
        return self.email['Subject']

    def __getstate__(self):
        data = DataType.DataType.__getstate__(self)
        data['email'] = self.get_email_string()
        return data

    def __setstate__(self, data):
        self.set_from_email_string(data['email'])
        DataType.DataType.__setstate__(self, data)

    def get_hash(self):
        return str(hash( self.get_email_string() ))
        
