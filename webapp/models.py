from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

# A USER class is required if we want to take advantage of Flasks-login-extension
# the user class has to support certain methods
# s. https://boh717.github.io/post/flask-login-and-mongodb/

class User():

    def __init__(self, email, db):
        #query user from mongo db with email (as unique identifier)
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
