# WSGI erwartet eine Variable 'application'
#https://stackoverflow.com/questions/28048342/how-do-i-configure-the-name-of-my-wsgi-application-on-aws-elastic-beanstalk

# Tipps und Tricks zu Import-Pfaden in Python
#https://realpython.com/absolute-vs-relative-python-imports/

#WICHTIG: Bug in Werkzeug --> muss daher mind. Version 0.15.5 sein!

from ROOT.webapp import app as application


