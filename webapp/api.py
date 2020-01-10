from flask import Blueprint, render_template, redirect, url_for, request, flash, send_file
from flask_restplus import Api, Resource, reqparse
from flask_login import login_user, logout_user, login_required, current_user
from . import app, db, ACTIVE_CONFIG
from .UserManagement import User
from bson.objectid import ObjectId
import os
import werkzeug

api_blueprint  = Blueprint('api', __name__)
api = Api(api_blueprint)

# LOGIN 

login_parser = reqparse.RequestParser()
login_parser.add_argument("email", type=str, location="form")
login_parser.add_argument("password", type=str, location="form")

class Login(Resource):
    @api.expect(login_parser)
    def post(self):
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.users.find_one({"email": email})

        if user and User.validate_login(user['password'], password): 
            user_obj = User(user['email'], db)
            login_user(user_obj)
            return {"message":"You are logged in now"}, 200
        else:
            return {"message":"Wrong credentials"}, 401

api.add_resource(Login, '/login')

# LOGOUT

class Logout(Resource):
    def post(self):
        if current_user.is_authenticated:
            logout_user()
            return {"message":"logout OK"}, 200
        else:
            return {"message":"You have to be logged in, to logout"}, 401

api.add_resource(Logout, '/logout')

# FILE UPLOAD

from .FileManagement import FileManagement
fm = FileManagement (current_user, db, app.config)

file_upload_parser = reqparse.RequestParser()
file_upload_parser.add_argument(
                        'file',  
                         type=werkzeug.datastructures.FileStorage, 
                         location='files', 
                         required=True,
                         help="any file")

class Files_Upload (Resource):
    @api.expect(file_upload_parser)
    def post (self):
        if not current_user.is_authenticated:
            return {"message":"please log in"}, 401
        else:
            if 'file' not in request.files:
                return {"message":"no file"}, 204

            file = request.files['file']

            if file.filename == '':
                return {"message":"no filename"}, 204

            if file and fm.allowed_file(file.filename):
                ret, file_id = fm.save (file)
                if ret == fm.FILE_CREATED:
                    return {"message":"File '"+file.filename+"' successfully uploaded",
                            "file_id":file_id}
                elif ret == fm.FILE_UPDATED:
                    return {"message":"File '"+file.filename+"' successfully updated",
                            "file_id":file_id}
            else:
                return {"message": "Allowed file types are "+str(fm.allowed_filetypes())}

api.add_resource(Files_Upload, '/files')

# FILE DOWNLOAD

class Files(Resource):
    
    def get (self, file_id):
        if current_user.is_authenticated:
            ret, filepath = fm.get_filepath(file_id)
            if ret == fm.FILE_EXISTS:
                return send_file(filepath)
            else:
                return "{'error': 'File not found'}", 404 
        else: 
            return {"message":"You have to be logged in"}, 401

api.add_resource(Files, '/files/<file_id>')

# QR CODE FOR FILE

class Files_QR_code(Resource):
    def get (self, file_id):
        img_io = fm.qrcode (file_id)
        return send_file(img_io, mimetype='image/jpeg')

api.add_resource(Files_QR_code, '/files/<file_id>/qrcode')
