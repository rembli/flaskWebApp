#####################################################################
# CONFIG
import yaml
import os

cwd = os.path.dirname(os.path.realpath(__file__))
config_path = os.path.join (cwd, "..", "config.yml")
with open(config_path, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

v = cfg['DEV_HOSTS']
print (v)
print ("localhost" in v)

v = cfg['DEV']["MONGO_DB_URI"]
print (v)

c = cfg['DEV']
cv = c["MONGO_DB_URI"]
print (cv)

exit()

#####################################################################
# HOSTNAME

# Importing socket library 
import socket 
  
# Function to display hostname and 
# IP address 
def get_Host_name_IP(): 
    try: 
        host_name = socket.gethostname() 
        host_ip = socket.gethostbyname(host_name) 
        print("Hostname :  ",host_name) 
        print("IP : ",host_ip) 
    except: 
        print("Unable to get Hostname and IP") 
  
# Driver code 
get_Host_name_IP() #Function call 

exit()

#####################################################################
# LAB for MongoDB

from pymongo import MongoClient
# connect tp Mongo server
client = MongoClient('localhost', 27017)
# connect or create database
db = client ["eic"]
# connect or create collection
userCollection = db ["user"]

# delete collection, i.e. all documents
userCollection.drop()

# insert document
userDocument = userCollection.insert_one ({
    "email": "georg.boegerl@web.de",
    "firstname": "Georg",
    "lastname": "Bögerl",
    "password": "123"
})
# get created ID
userID = userDocument.inserted_id
# print document ID
print ("new user", userID)

# query & print user
from pprint import pprint
queryResult = userCollection.find({})
for userDocument in queryResult: 
    pprint(userDocument)

# query collection
totalUserDocuments = userCollection.count_documents({})
print ("number of user", totalUserDocuments)

exit()
