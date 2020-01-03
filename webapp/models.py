from werkzeug.security import generate_password_hash, check_password_hash

# A USER class is required if we want to take advantage of Flasks-login-extension
# the user class has to support certain methods
# s. https://boh717.github.io/post/flask-login-and-mongodb/

class User():
    
    def __init__(self, email, db):
        #query user from mongo db with email (as unique identifier)
        user = db.users.find_one({"email": email})

        self.email = email
        self.name = user["name"] # set username to name from mongodb-document

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.email
        
    @staticmethod
    def validate_login(password_hash, password):
        return check_password_hash(password_hash, password)
