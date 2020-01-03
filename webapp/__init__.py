import os, yaml, socket
from flask import Flask, request
from flask_login import LoginManager 
from pymongo import MongoClient
from .models import User

# INIT FLASK APP

app = Flask(__name__)

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
app.config['ALLOWED_EXTENSIONS'] = cfg["ALLOWED_EXTENSIONS"]
app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024

# CONNNECT TO MONGO

db = MongoClient(app.config['MONGO_DB_URI'])["eic"]

# INIT FLASK LOGIN MANAGER

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)    

# We need a user_loader function to reload the user object through different sessions. This function must satisfy three conditions:
# - it takes the unicode ID of a user;
# - it returns the user object;
# - if the ID is invalid must return None.

@login_manager.user_loader
def load_user(email):
    # query mongo or user with given email
    u = db.users.find_one({"email": email})
    if u:
        # if user was found in db return User object
        return User(u['email'], db)
    else:
        return None
 

# INCLUDE BLUEPRINTS FOR DIFFERENT PARTS OF THE APP

# blueprint for auth routes in our app
from .auth import auth as auth_blueprint
app.register_blueprint(auth_blueprint)

# blueprint for non-auth parts of app
from .main import main as main_blueprint
app.register_blueprint(main_blueprint)


