from flask import Flask, Blueprint, render_template, flash, request, redirect, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os, datetime
from . import app, db, ACTIVE_CONFIG
from bson.objectid import ObjectId
import pymongo
import re
import qrcode
from io import BytesIO

main = Blueprint('main', __name__)

# HOMEPAGE

@main.route('/')
def index():
    num_users = db.users.count_documents({})
    num_files = db.files.count_documents({})    
    return render_template('index.html', num_users=num_users, num_files=num_files)

# FILE MANAGEMENT
from .FileManagement import FileManagement
fm = FileManagement (current_user, db, app.config)

@main.route('/upload')
@login_required
def upload():
    return render_template('upload.html')

@main.route('/upload', methods=['POST'])
def upload_post():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(request.url)

    if file and fm.allowed_file(file.filename):
        ret = fm.save (file)
        if ret == fm.FILE_CREATED:
            flash("File '"+file.filename+"' successfully uploaded")
        elif ret == fm.FILE_UPDATED:
            flash("File '"+file.filename+"' successfully updated")
        return render_template('upload.html')

    else:
        flash('Allowed file types are '+str(app.config['ALLOWED_EXTENSIONS'] ))
        return redirect(request.url)

@main.route('/files')
@login_required
def files():
    query_string = request.args.get('query_string')
    files = fm.query (query_string)
    return render_template('files.html', files=files, query_string=query_string)

@main.route('/files/<file_id>')
@login_required
def files_download(file_id):

    ret, filepath = fm.get_filepath(file_id)

    if ret == fm.FILE_EXISTS:
        return send_file(filepath)
    else:
        return "{'error': 'File not found'}", 404 

@main.route('/files/<file_id>/qrcode')
@login_required
def files_qrcode(file_id):
    img_io = fm.qrcode(file_id)
    return send_file(img_io, mimetype='image/jpeg')

'''
# FILE UPLOAD
#s. https://www.roytuts.com/python-flask-file-upload-example/

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'] 

@main.route('/upload')
@login_required
def upload():
    return render_template('upload.html')

@main.route('/upload', methods=['POST'])
def upload_post():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        current_time = datetime.datetime.now() 
        current_user_id = current_user.get_internal_id()

        # WHOLE FILE UPLOAD SHOULD BE A TRANSACTION
        filename = secure_filename(file.filename)
        # OLD: filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "__filecache__", filename)
        filepath = os.path.join(root_path(), app.config['FILE_UPLOAD_PATH'], current_user_id)
        if not os.path.exists(filepath):
            os.makedirs (filepath)
        file.save (os.path.join(filepath, filename))

        # query if file exists fpr this user
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
            
            flash("File '"+filename+"' successfully uploaded")
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
            
            flash("File '"+filename+"' successfully updated")

        return render_template('upload.html')

    else:
        flash('Allowed file types are '+str(app.config['ALLOWED_EXTENSIONS'] ))
        return redirect(request.url)
        

@main.route('/files')
@login_required
def files():
    query_string = request.args.get('query_string')
    if query_string is None or len(query_string) == 0:
        files = db.files.find({"created_by": current_user.get_internal_id()}).limit(100).sort([("filename", pymongo.ASCENDING)])
    else:
        files = db.files.find(
            {"$and":[{"created_by": current_user.get_internal_id()},{"filename": {'$regex': re.compile(query_string, re.IGNORECASE)}}]}    
            ).limit(100).sort([("filename", pymongo.ASCENDING)])
        
    return render_template('files.html', files=files, query_string=query_string)


@main.route('/files/<file_id>')
@login_required
def files_download(file_id):
    file = db.files.find_one({"_id": ObjectId(file_id)}) 
    if file:
        filepath_filename = os.path.join(file["filepath"], file["filename"])
        return send_file(filepath_filename)
    else:
        return "{'error': 'File not found'}", 404 


@main.route('/files/<file_id>/qrcode')
@login_required
def files_qrcode(file_id):
    img_io = BytesIO()
    img = qrcode.make("http://rembli.com/files/"+file_id)
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

'''