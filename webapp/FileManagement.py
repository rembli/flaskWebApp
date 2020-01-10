from . import app, db, ACTIVE_CONFIG
import os, datetime
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import pymongo, re
import qrcode
from io import BytesIO

class FileManagement():
    FILE_CREATED = 1
    FILE_UPDATED = 2
    FILE_TYPE_NOT_ALLOWED = 3
    FILE_NOT_FOUND = 4
    FILE_EXISTS = 5

    def __init__(self, current_user, db, config):    
        self.current_user = current_user
        self.db = db
        self.config = config

    def allowed_filetypes(self):
        return self.config['ALLOWED_EXTENSIONS']

    def allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_filetypes()

    def save(self, file):
        current_time = datetime.datetime.now() 
        current_user_id = self.current_user.get_internal_id()

        # save file to disk
        filename = secure_filename(file.filename)
        filepath = os.path.join(FileManagement.root_path(), self.config['FILE_UPLOAD_PATH'], current_user_id)
        if not os.path.exists(filepath):
            os.makedirs (filepath)
        file.save (os.path.join(filepath, filename))

        # query if file exists for this user
        file_exsists = db.files.find_one({"$and":[{"filepath":filepath},{"filename":filename}]})

        if not file_exsists: 
        # file has not been uploaded before
            new_file = { 
                "filepath": filepath, 
                "filename": filename, 
                "created_on": current_time,
                "created_by": current_user_id
            }
            new_file_obj = db.files.insert_one(new_file)    
            
            event_ref = "/files/"+current_user_id+"/"+str(new_file_obj.inserted_id)
            new_event = { 
                "event_type": "FILE_CREATED", 
                "event_ref": event_ref,
                "created_on": current_time,
                "created_by": current_user_id
            }
            new_event_obj = db.events.insert_one(new_event)  
            
            return FileManagement.FILE_CREATED, str(new_file_obj.inserted_id)
        else:
        # file has been alread uploaded before      
            event_ref = "/files/"+current_user_id+"/"+str(file_exsists.get("_id"))
            new_event = { 
                "event_type": "FILE_UPDATED", 
                "event_ref": event_ref,
                "created_on": current_time,
                "created_by": current_user_id
            }
            new_event_obj = db.events.insert_one(new_event)           
            
            return FileManagement.FILE_UPDATED, str(file_exsists.get("_id"))
            
    def query (self, query_string):
        if query_string is None or len(query_string) == 0:
            files = db.files.find({"created_by": self.current_user.get_internal_id()}).limit(100).sort([("filename", pymongo.ASCENDING)])
        else:
            files = db.files.find(
                {"$and":[{"created_by": self.current_user.get_internal_id()},{"filename": {'$regex': re.compile(query_string, re.IGNORECASE)}}]}    
                ).limit(100).sort([("filename", pymongo.ASCENDING)])
        return files


    def get_filepath (self, file_id):
        file = db.files.find_one({"_id": ObjectId(file_id)}) 
        if file:
            filepath_filename = os.path.join(file["filepath"], file["filename"])
            return FileManagement.FILE_EXISTS, filepath_filename
        else:
            return FileManagement.FILE_NOT_FOUND

    def qrcode(self, file_id):
        img_io = BytesIO()
        img = qrcode.make("http://rembli.com/files/"+file_id)
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return img_io
   
    @staticmethod
    def root_path():
        return os.path.abspath(os.sep)
