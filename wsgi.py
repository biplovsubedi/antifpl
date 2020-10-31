""" 
File is used to start Flask application 

Used by heroku

Note: Setup Procfile with following value to start the server
web: gunicorn wsgi:app

Flask app in app.fpl 
"""

from app.fpl import fplapp

if __name__ == "__main__":
    fplapp.run()
