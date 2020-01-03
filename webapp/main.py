from flask import Flask, Blueprint, render_template, flash, request, redirect
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from . import app, db, ACTIVE_CONFIG

main = Blueprint('main', __name__)

# HOMEPAGE

@main.route('/')
def index():
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
        # file will be temporarly saved in the folder __filecache__ just beneath this python script main.py
        filename = secure_filename(file.filename)
        filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "__filecache__", filename)
        file.save(filepath)
        
        flash('File successfully uploaded')
        return render_template('upload.html')

    else:
        flash('Allowed file types are '+str(app.config['ALLOWED_EXTENSIONS'] ))
        return redirect(request.url)
        


# USER PROFILE

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name, email=current_user.email)

