from flask import Flask, Blueprint, render_template, flash, request, redirect, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, datetime
from bson.objectid import ObjectId
from bson.json_util import dumps
import pymongo, re
import qrcode
from io import BytesIO

from . import app, db, ACTIVE_CONFIG, accept_json

#############################################################################
# MODEL
#############################################################################

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
            db.events.insert_one(new_event)  
            
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
            db.events.insert_one(new_event)           
            
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

#############################################################################
# API
#############################################################################

fm = FileManagement (current_user, db, app.config)

fbp = Blueprint('files', __name__)

# FILE MANAGEMENT

@fbp.route('/upload')
@login_required
def upload():
    return render_template('upload.html')


@fbp.route('/upload', methods=['POST'])
@login_required
def upload_post():
    """ uploaded file
    ---
    tags:
        - files management
    parameters:
        - in: formData
          name: file
          type: file
    responses:
         200:
            description: list of files that match the query
    """ 
    msg = None
    if 'file' not in request.files:
        msg = "No file part"
    else:
        file = request.files['file']
        if not file or file.filename == '':
            msg = "No file selected for uploading"
        else:
            if not fm.allowed_file(file.filename):
                msg = "Allowed file types are " + str(app.config["ALLOWED_EXTENSIONS"])
            else:
                ret, id = fm.save (file)
                if ret == fm.FILE_UPDATED:
                    msg = "File '"+file.filename+"' successfully updated"
                else:
                    msg = "File '"+file.filename+"' successfully uploaded"
    
    if accept_json (request):
        return jsonify({"message": msg })
    else:
        if msg:
            flash(msg)
        return render_template('upload.html')

@fbp.route('/files')
@login_required
def files():
    """ query uploaded files
    ---
    tags:
        - files management
    parameters:
      - name: q
        in: query
        type: string
    responses:
      200:
        description: list of files that match the query
    """    
    q = request.args.get('q')
    files = fm.query (q)

    print (request.headers.get("accept"))

    if accept_json (request):
        return dumps (files)
    else:
        return render_template('files.html', files=files, q=q)


@fbp.route('/files/<file_id>')
#@login_required
def files_download(file_id):
    """ get file
    ---
    tags:
        - files management    
    parameters:
      - name: file_id
        in: path
        type: string    
    responses:
      200:
        description: file
    """
    ret, filepath = fm.get_filepath(file_id)

    if ret == fm.FILE_EXISTS:
        return send_file(filepath)
    else:
        return "{'error': 'File not found'}", 404 


@fbp.route('/files/<file_id>/qrcode')
@login_required
def files_qrcode(file_id):
    """ get qrcode for file
    ---
    tags:
        - files management   
    parameters:
      - name: file_id
        in: path
        type: string    
    responses:
      200:
        description: qr code
    """   
    img_io = fm.qrcode(file_id)
    return send_file(img_io, mimetype='image/jpeg')
