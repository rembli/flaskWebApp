# https://www.thepythoncode.com/article/reading-emails-in-python

from .auth import User
from .files import FileManagement

import imaplib
import email
from email.header import decode_header

from bson.objectid import ObjectId
from tempfile import TemporaryFile
import os
import sys
import traceback

#############################################################################
# MODEL
#############################################################################

class EMailManagement ():

    def __init__(self, db, config):
        self.db = db
        self.config = config
    
    def import_mails(self):

        # login to email bix
        M = imaplib.IMAP4_SSL(self.config['MAIL_IMAP'])
        M.login(self.config['MAIL_USERNAME'], self.config['MAIL_PASSWORD'])
        M.select()

        # get all emails
        res, msg_uid_list = M.uid('search', None, 'ALL')
        
        # iterate through emails
        for msg_uid in msg_uid_list[0].split():
            res, msg_data = M.uid('fetch', msg_uid, '(RFC822)')

            # convert 
            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            smsg = msg.as_bytes().decode(encoding='ISO-8859-1')

            # dump email to db
            filename = subject + ".eml"
            FileManagement.save_email (self.db, self.config, msg["to"], filename, smsg)

            ''' dump email to file
            filename = EMailManagement.E_MAIL_FOLDER + os.sep + msg_uid.decode("utf-8") + ".eml"
            with open(filename, 'w', encoding="utf-8") as f:
                f.write(smsg)
            '''
            
            # set email to deleted
            M.uid('STORE', msg_uid, '+FLAGS', '\\Deleted')            

        M.close()
        M.logout()
