from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from pymongo import MongoClient

from .config import Config
from . import models

# Initialize extensions, but don't configure them yet
cors = CORS()
bcrypt = Bcrypt()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Initialize Extensions with the App ---
    cors.init_app(app, supports_credentials=True) # supports_credentials is key for sessions
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Configure the database connection
    client = MongoClient(app.config['MONGO_URI'])
    # db = client.get_default_database() # Get the DB name from the URI
    db = client['email_tracker_v2'] 
    # Make the db instance available to the models module
    models.db = db

    # --- User Loader for Flask-Login ---
    # This tells Flask-Login how to load a user from the DB given a user ID
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.find_by_id(user_id)

    # --- Register Blueprints ---
    from .auth import auth_bp
    from .tracking import tracking_bp
    from .api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tracking_bp) # No prefix for /track and /click
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def home():
        return {"status": "healthy", "message": "Welcome to Tracker v2.0 API"}

    return app