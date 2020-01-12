import os, yaml, socket
from flask import Flask, jsonify, request, render_template
from flask_restplus import Api
from flask_login import LoginManager 
from flasgger import Swagger
from pymongo import MongoClient

# INIT FLASK APP

app = Flask(__name__)

# SET CACHE CONTROL

@app.after_request
def add_header(response):
    response.cache_control.max_age = 10
    return response

# HELPER FUNCTIONS

def accept_json (request):
    return request.headers.get("accept") == "application/json"

# LOAD CONFIG
# load the config.yml file

cwd = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join (cwd, "..", "config.yml")
with open(config_path, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

# Decide on environment depending on the current host that we get from a socket connection
# Unfortuntatly it is not localhost but the name of the machine
# At this moment we cannot take the information from the request (because there is no request, the app is still initialising)

ACTIVE_CONFIG = "PRD"
host_name = socket.gethostname() 
if host_name in cfg["DEV_HOSTS"]:
    ACTIVE_CONFIG = "DEV"

app.config['SECRET_KEY'] = cfg[ACTIVE_CONFIG]["SECRET_KEY"]
app.config['MONGO_DB_URI'] = cfg[ACTIVE_CONFIG]["MONGO_DB_URI"]
app.config['MONGO_DB_NAME'] = cfg[ACTIVE_CONFIG]["MONGO_DB_NAME"]
app.config['FILE_UPLOAD_PATH'] = cfg[ACTIVE_CONFIG]["FILE_UPLOAD_PATH"]
app.config['ALLOWED_EXTENSIONS'] = cfg["ALLOWED_EXTENSIONS"]
app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024

# CONNNECT TO MONGO

db = MongoClient(app.config['MONGO_DB_URI'])[app.config['MONGO_DB_NAME']]

# INIT FLASK LOGIN MANAGER

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)    

# We need a user_loader function to reload the user object through different sessions. This function must satisfy three conditions:
# - it takes the unicode ID of a user;
# - it returns the user object;
# - if the ID is invalid must return None.

from .auth import User

@login_manager.user_loader
def load_user(email):
    # query mongo or user with given email
    u = db.users.find_one({"email": email})
    if u:
        # if user was found in db return User object
        return User(u['email'], db)
    else:
        return None

# ADD SWAGGER

swagger = Swagger(app)

# HOMEPAGE

@app.route('/')
def index():
    num_users = db.users.count_documents({})
    num_files = db.files.count_documents({})    
    return render_template('index.html', num_users=num_users, num_files=num_files)


# INCLUDE BLUEPRINTS FOR DIFFERENT PARTS OF THE APP

# blueprint for auth routes in our app
from .auth import abp
app.register_blueprint(abp)

# blueprint for non-auth parts of app
from .files import fbp
app.register_blueprint(fbp)
