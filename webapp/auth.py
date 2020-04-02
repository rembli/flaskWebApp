from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import base64, re, hashlib, os, urllib, requests, json, jwt
import string
from secrets import choice

from . import app, db, ACTIVE_CONFIG, accept_json, logger


####################################################
# MODEL
####################################################

# A USER class is required if we want to take advantage of Flasks-login-extension
# the user class has to support certain methods
# s. https://boh717.github.io/post/flask-login-and-mongodb/

class User():

    def __init__(self, email, db):
        #query user from mongo db with email (as unique identifier)
        self.db = db
        user_obj = db.users.find_one({"email": email})
        
        self.email = email
        self.name = user_obj["name"] # set username to name from mongodb-document
        self.id = str(user_obj["_id"])

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.email
        
    def get_internal_id(self):
        return self.id
        
    def get_name(self):
        return self.name

    def get_email(self):
        return self.email

    @staticmethod
    def validate_login(password_hash, password):
        return check_password_hash(password_hash, password)


####################################################
# API
####################################################

# DECLARE FLASK BLUEPRINT

abp = Blueprint('auth', __name__)

# LOGIN-URI

@abp.route('/login')
def login():
    if accept_json(request):
        return jsonify({"message":"please log in"}), 401
    else:
        return render_template('login.html')


@abp.route('/login', methods=['POST'])
def login_post():
    """ login
    ---
    tags:
        - user management     
    parameters:
        - in: formData
          name: email
          type: string
        - in: formData
          name: password
          type: password
    responses:
         200:
            description: login user
    """     

    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False
    
    # query email in mongo user collection
    user = db.users.find_one({"email": email})

    msg = None
    fun = None

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not User.validate_login(user['password'], password): 
        msg = "Please check your login details and try again."
        fun = lambda: redirect(url_for('auth.login')) # if user doesn't exist or password is wrong, reload the page
    else:
        # if the above check passes, then we know the user has provided the right credentials
        user_obj = User(user['email'], db) # load user data from DB and instantiate custom user object
        login_user(user_obj, remember=remember) # provide user object to flask login manager
        msg = "login success"
        fun = lambda: redirect(url_for('auth.profile'))
    
    if accept_json (request):
        return jsonify ({"message": msg})
    else:
        if msg:
            flash (msg)
        return fun()


####################################################
# LOGIN WITH DATEV (OIDC)
####################################################

# https://www.stefaanlippens.net/oauth-code-flow-pkce.html
# https://developer.byu.edu/docs/consume-api/use-api/oauth-20/oauth-20-python-sample-code 
# https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html 

# copy from https://github.com/OpenIDC/pyoidc/blob/master/src/oic/__init__.py 
# Return a string of random ascii characters or digits.
def rndstr(size=16):
    _basech = string.ascii_letters + string.digits
    return "".join([choice(_basech) for _ in range(size)])

# https://login.datev.de/openidsandbox/.well-known/openid-configuration") 
authorization_url = 'https://login.datev.de/openidsandbox/authorize'
token_url = 'https://sandbox-api.datev.de/token'
redirect_url = 'https://rembli.com/login_with_DATEV'
userinfo_url = 'https://sandbox-api.datev.de/userinfo'

client_id = app.config['OIDC_CLIENT_ID']
client_secret = app.config['OIDC_CLIENT_SECRET']

@abp.route('/init_login_with_DATEV')
def init_login_with_DATEV():
    """Step 1: User Authorization.
    Redirect the user/resource owner to the OAuth provider 
    using an URL with a few key OAuth parameters.
    """
    code_verifier = base64.urlsafe_b64encode(os.urandom(64)).decode('utf-8')
    code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
    session["code_verifier"] = code_verifier

    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
    code_challenge = code_challenge.replace('=', '')

    session["state"] = rndstr(42)
    session["nonce"] = rndstr(42)

    args = {
        "client_id": client_id,
        "response_type": "code id_token",
        "scope": "openid profile extended_profile email accounting:documents",
        "redirect_uri": redirect_url,
        "nonce": session["nonce"],        
        "state": session["state"],
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",     
        "response_mode":"query"
    }

    login_url = authorization_url+"?"+urllib.parse.urlencode(args)
    return redirect(login_url)        


@abp.route('/login_with_DATEV')
def login_with_DATEV():
    """ Step 2: User authorization: this happens in the browser after the above redirect. """

    """ Step 3: Retrieving an access token.
    The user has been redirected back from the provider to our registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    We store the toke in the session so that we can use it for various api calls
    """

    credential = client_id + ":" + client_secret
    encodedBytes = base64.b64encode(credential.encode("utf-8"))
    encodedStr = str(encodedBytes, "utf-8")
    auth_header = "Basic " + encodedStr

    query = urllib.parse.urlparse(request.url).query
    redirect_params = urllib.parse.parse_qs(query)
    auth_code = redirect_params['code'][0]

    code_verifier = session["code_verifier"]

    response = requests.post(
        url=token_url,
        headers={'Authorization': auth_header},
        data={
            "redirect_uri": redirect_url,
            "code": auth_code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code"
        },
        allow_redirects=False
    )
    logger.debug (response.text)

    tokens = response.json()

    # id_token_json = jwt.decode(tokens['id_token'], verify=False)
    # logger.debug (json.dumps(id_token_json))

    """ Step 4: Access UserInfo API 
    """

    response = requests.get (
        url=userinfo_url,
        headers={
            "Authorization": "Bearer " + tokens['access_token'],
            "X-Datev-Client-Id": client_id,
            "X-Requested-With": "XMLHttpRequest"
        },
        verify=False
    )    
    logger.debug (response.text)
    ''' sample response for user info:
        {   "name" : "Georg Boegerl", 
            "email" : "Georg.boegerl@web.de", 
            "given_name" : "Georg", 
            "family_name" : "Boegerl", 
            "email_verified" : false, 
            "sub" : "7m7aPB1ztK/Gn6Ybj6X/47KNqQ2lJqIuMT8E6gG2JGg=", 
            "person_id" : "0004577334" 
        } 
    '''
    userinfo = response.json()
    email = userinfo['email']
    name = userinfo['name']
    password = rndstr (64)

    # check if user already exists
    user = db.users.find_one({"email": email})

    # if user does not exist, create user profuke
    if not user:
        new_user = { 
            "email": email, 
            "name": name, 
            "password": generate_password_hash(password, method='sha256')
        }
        db.users.insert_one(new_user)
        user = db.users.find_one({"email": email})

    # login user
    user_obj = User(user['email'], db) # load user data from DB and instantiate custom user object
    login_user(user_obj) # provide user object to flask login manager
 
    return redirect(url_for('auth.profile'))      


# LOGOUT-URI

@abp.route('/logout')
@login_required
def logout():
    """ logout
    ---
    tags:
        - user management     
    responses:
         200:
            description: logout user
    """ 
    logout_user()
    if accept_json(request):
        return jsonify ({"message":"logout successful"})
    else:
        return redirect(url_for('index'))


# REGISTER-URI

@abp.route('/register')
def register():
    return render_template('register.html')

@abp.route('/register', methods=['POST'])
def register_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    # query email in mongo user collection
    user = db.users.find_one({"email": email}) # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('auth.register'))

    # insert new user with the form data into db. Hash the password so plaintext version isn't saved.
    new_user = { 
        "email": email, 
        "name": name, 
        "password": generate_password_hash(password, method='sha256')
    }
    db.users.insert_one(new_user)

    return redirect(url_for('auth.login'))


# USER PROFILE-URI

@abp.route('/profile')
@login_required
def profile():
    # clear all flash messages
    session.pop('_flashes', None)
    return render_template('profile.html', name=current_user.name, email=current_user.email)
