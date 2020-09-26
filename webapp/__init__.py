import os, yaml, socket
from flask import Flask, jsonify, request, render_template, session
from flask_login import LoginManager, login_required, current_user
from flasgger import Swagger
from flask_pymongo import PyMongo
from flask_apscheduler import APScheduler
import logging
import contextlib
import http.client


#####################################################
# INIT FLASK APP
#####################################################

app = Flask(__name__)
app.secret_key = os.urandom(24)

# SET CACHE CONTROL

@app.after_request
def add_header(response):
    response.cache_control.max_age = 10
    return response

# HELPER FUNCTIONS

def accept_json (request):
    return request.headers.get("accept") == "application/json"


#####################################################
# LOAD CONFIG DEV/PRD
#####################################################

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
app.config['MONGO_URI'] = cfg[ACTIVE_CONFIG]["MONGO_URI"]
app.config['FILE_UPLOAD_PATH'] = cfg[ACTIVE_CONFIG]["FILE_UPLOAD_PATH"]
app.config['ALLOWED_EXTENSIONS'] = cfg["ALLOWED_EXTENSIONS"]
app.config['MAX_CONTENT_LENGTH'] = 16*1024*1024
app.config['OIDC_CLIENT_ID'] = cfg[ACTIVE_CONFIG]["OIDC_CLIENT_ID"]
app.config['OIDC_CLIENT_SECRET'] = cfg[ACTIVE_CONFIG]["OIDC_CLIENT_SECRET"]
app.config['MAIL_IMAP'] = cfg[ACTIVE_CONFIG]["MAIL_IMAP"]
app.config['MAIL_USERNAME'] = cfg[ACTIVE_CONFIG]["MAIL_USERNAME"]
app.config['MAIL_PASSWORD'] = cfg[ACTIVE_CONFIG]["MAIL_PASSWORD"]


#####################################################
# LOGGING
#####################################################

# CONFIGURE LOGGING

log_path = os.path.join (cwd, "..", "logs", "http.log")
logging.basicConfig(filename=log_path, level=logging.DEBUG)
logger = logging.getLogger ()

# ENABLE HTTP LOGGING

httpclient_logger = logging.getLogger("http.client")
httpclient_logger.setLevel(logging.DEBUG)
httpclient_logger.propagate = True

def httpclient_log(*args):
    httpclient_logger.log(logging.DEBUG, " ".join(args))

http.client.print = httpclient_log
http.client.HTTPConnection.debuglevel = 1


#####################################################
# DB CONNECTIVITY
#####################################################

# CONNNECT TO MONGO
mongo = PyMongo(app)
db = mongo.db


#####################################################
# USER LOGIN MANAGEMENT
#####################################################

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


#####################################################
# SWAGGER UU
#####################################################

swagger = Swagger(app)


#####################################################
# HOMEPAGE
#####################################################

@app.route('/')
def index():
    num_users = db.users.count_documents({})
    num_files = db.files.count_documents({})    
    return render_template('index.html', num_users=num_users, num_files=num_files)

@app.route('/portal')
def portal():
    is_DATEV_session = False
    try:
        is_DATEV_session = session['is_DATEV_session']
    except:
        pass
    return render_template('portal.html', is_DATEV_session = is_DATEV_session)    


######################################################
# INCLUDE BLUEPRINTS FOR DIFFERENT PARTS OF THE APP
######################################################

# blueprint for auth routes in our app
from .auth import abp
app.register_blueprint(abp)

# blueprint for non-auth parts of app
from .files import fbp
app.register_blueprint(fbp)


######################################################
# ADD BACKGROUND TASK
######################################################

from .emails import EMailManagement
EM = EMailManagement (db, app.config)

scheduler = APScheduler()

@scheduler.task('interval', id='check emails', seconds=30, misfire_grace_time=900)
def job_read_emails():
    logger.info("* import emails from inbox")
    EM.import_mails()

scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()
logger.info("* Job scheduler started")
