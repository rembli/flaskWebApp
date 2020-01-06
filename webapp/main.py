from flask import Flask, Blueprint, render_template, flash, request, redirect
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
from . import app, db, ACTIVE_CONFIG
from .helper import root_path

main = Blueprint('main', __name__)

# HOMEPAGE

@main.route('/')
def index():
    print (root_path())
    return render_template('index.html')


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
        filename = secure_filename(file.filename)
        # old: file will be temporarly saved in the folder __filecache__ just beneath this python script main.py
        # old: filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "__filecache__", filename)
        filepath = os.path.join(root_path(), app.config['FILE_UPLOAD_PATH'], filename)
        file.save(filepath)
        
        flash('File successfully uploaded')
        return render_template('upload.html')

    else:
        flash('Allowed file types are '+str(app.config['ALLOWED_EXTENSIONS'] ))
        return redirect(request.url)
        
