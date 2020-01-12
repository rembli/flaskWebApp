from flask import Flask, Blueprint, render_template, flash, request, redirect, send_file, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, datetime
from bson.objectid import ObjectId
from bson.json_util import dumps
import pymongo, re
import qrcode
from io import BytesIO

from . import app, db, ACTIVE_CONFIG

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

#############################################################################
# API
#############################################################################

files_blueprint = Blueprint('files', __name__)

# FILE MANAGEMENT
fm = FileManagement (current_user, db, app.config)

@files_blueprint.route('/upload')
@login_required
def upload():
    return render_template('upload.html')

@files_blueprint.route('/upload', methods=['POST'])
@login_required
def upload_post():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(request.url)

    if file and fm.allowed_file(file.filename):
        ret, id = fm.save (file)
        
        if ret == fm.FILE_CREATED:
            flash("File '"+file.filename+"' successfully uploaded")
        elif ret == fm.FILE_UPDATED:
            flash("File '"+file.filename+"' successfully updated")

        return render_template('upload.html')

    else:
        flash('Allowed file types are '+str(app.config['ALLOWED_EXTENSIONS'] ))
        return redirect(request.url)


@files_blueprint.route('/files')
@login_required
def files():
    """ query uploaded files
    ---
    parameters:
      - name: querystring
        in: query
        type: string
    responses:
      200:
        description: list of files that match the query
    """    
    query_string = request.args.get('query_string')
    files = fm.query (query_string)

    print (request.headers.get("accept"))
    if request.headers.get("accept") == "application/json":
        return dumps (files)
    else:
        return render_template('files.html', files=files, query_string=query_string)

@files_blueprint.route('/files/<file_id>')
#@login_required
def files_download(file_id):
    """ get file
    ---
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

@files_blueprint.route('/files/<file_id>/qrcode')
@login_required
def files_qrcode(file_id):
    """ get qrcode for file
    ---
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
