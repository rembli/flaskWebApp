from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db # get db-object from __init__.py
from .models import User # get User class from models.py

# DECLARE FLASK BLUEPRINT

auth = Blueprint('auth', __name__)

# LOGIN-URI

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    # query email in mongo user collection
    user = db.users.find_one({"email": email})

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not User.validate_login(user['password'], password): 
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has provided the right credentials
    user_obj = User(user['email'], db) # load user data from DB and instantiate custom user object
    login_user(user_obj, remember=remember) # provide user object to flask login manager
    return redirect(url_for('auth.profile'))

# REGISTER-URI

@auth.route('/register')
def register():
    return render_template('register.html')

@auth.route('/register', methods=['POST'])
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
    new_user_obj = db.users.insert_one(new_user)

    return redirect(url_for('auth.login'))

# USER PROFILE-URI

@auth.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name, email=current_user.email)

# LOGOUT-URI

@auth.route('/logout')
@login_required
def logout():
    logout_user() 
    return redirect(url_for('main.index'))
