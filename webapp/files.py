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

files_blueprint = Blueprint('files', __name__)

# FILE MANAGEMENT
from .FileManagement import FileManagement
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
    query_string = request.args.get('query_string')
    files = fm.query (query_string)
    return render_template('files.html', files=files, query_string=query_string)

@files_blueprint.route('/files/<file_id>')
#@login_required
def files_download(file_id):

    ret, filepath = fm.get_filepath(file_id)

    if ret == fm.FILE_EXISTS:
        return send_file(filepath)
    else:
        return "{'error': 'File not found'}", 404 

@files_blueprint.route('/files/<file_id>/qrcode')
@login_required
def files_qrcode(file_id):
    img_io = fm.qrcode(file_id)
    return send_file(img_io, mimetype='image/jpeg')
