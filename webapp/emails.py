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
    
    IS_READ_MESSAGE = True
    IS_DELETE_MESSAGE = True

    E_MAIL_FOLDER = "C:\Data\Dev\PythonLab\FlaskWebAppProject\emails"

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
            print("From:", msg["from"])
            print("To:", msg["to"])

            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            print ("Subject:", subject)

            smsg = msg.as_bytes().decode(encoding='ISO-8859-1')

            # dump email to db
            filename = subject + ".eml"
            FileManagement.save_email (self.db, self.config, msg["to"], filename, smsg)

            ''' dump email to file
            filename = EMailManagement.E_MAIL_FOLDER + os.sep + msg_uid.decode("utf-8") + ".eml"
            with open(filename, 'w', encoding="utf-8") as f:
                f.write(smsg)
            '''

            # display content and attachments 
            '''
            for msg_data_parts in msg_data:
                if isinstance(msg_data_parts, tuple):
                    # parse a bytes email into a message object
                    msg = email.message_from_bytes(msg_data_parts[1])

                    subject = decode_header(msg["Subject"])[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode()

                    print("Subject:", subject)
                    
                    # if the email message is no multipart
                    if not msg.is_multipart():
                        content_type = msg.get_content_type()
                        body = msg.get_payload(decode=True).decode()
                        # print(body)

                    # email is multipart
                    else:
                        cnt = 0
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))

                            if "attachment" in content_disposition:
                                filename = part.get_filename()
                                print ("--- ATTACHMENT: ", filename)       

                            else:
                                try:
                                    body = part.get_payload(decode=True)
                                    # print(body)
                                except:
                                    pass
                            cnt = cnt + 1
                print("="*100)
                '''
            # set email to deleted
            M.uid('STORE', msg_uid, '+FLAGS', '\\Deleted')
            
            # except:
                # exc_info = sys.exc_info()
                # traceback.print_exception(*exc_info)

        M.close()
        M.logout()
