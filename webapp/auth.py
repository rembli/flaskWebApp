from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

from . import app, db, ACTIVE_CONFIG, accept_json

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
    #next_url = request.form.get('next')

    # query email in mongo user collection
    user = db.users.find_one({"email": email})

    success = False
    msg = None
    fun = None

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not User.validate_login(user['password'], password): 
        msg = "Please check your login details and try again."
        fun = lambda: redirect(url_for('auth.login')) # if user doesn't exist or password is wrong, reload the page
    else:
        # if the above check passes, then we know the user has provided the right credentials
        success = True
        user_obj = User(user['email'], db) # load user data from DB and instantiate custom user object
        login_user(user_obj, remember=remember) # provide user object to flask login manager
        fun = lambda: redirect(url_for('auth.profile'))
    
    if accept_json (request):
        if success:
            msg = "login success"
        return jsonify ({"message": msg})
    else:
        if msg:
            flash (msg)
        return fun()

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
    return render_template('profile.html', name=current_user.name, email=current_user.email)
