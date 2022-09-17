from flask import Flask
import os,logging

from application import configuration
from application.configuration import LocalDevConfig
from application.database import db
from application.models import User, Role

from flask_security import Security, SQLAlchemySessionUserDatastore , SQLAlchemyUserDatastore , RegisterForm
from wtforms import StringField
from wtforms.validators import DataRequired

logging.basicConfig(filename='debug.log', level=logging.INFO, format='[%(levelname)s %(asctime)s %(name)s] ' + '%(message)s')

app = None

def create_app():
    #creates flask app 
    app = Flask(__name__ , template_folder = 'templates')

    #-------
    
    app.config.from_object(LocalDevConfig)

    #database initialization
    db.init_app(app)
    app.app_context().push()

    class Username_RegisterForm(RegisterForm):
        #additional field is added to the default register form of flask_security
        username = StringField('Full Name',[DataRequired()])

    user_datastore = SQLAlchemySessionUserDatastore(db.session , User , Role)
    #flask_security initialized 

    security = Security(app , user_datastore, register_form = Username_RegisterForm)
    #object current_user is created

    app.logger.info('Application setup is Complete')
    return app

app = create_app()

from application.controllers.home_page import *
from application.controllers.tracker import *
from application.controllers.log import *

if __name__ == '__main__':
    app.run(debug = True)
