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
    app.config.update(
        SESSION_COOKIE_SAMESITE='None', # Allows the cookie to be sent from different sites
        SESSION_COOKIE_SECURE=True,     # Requires HTTPS, which Render provides
        SESSION_COOKIE_HTTPONLY=True    # Prevents client-side JS from accessing the cookie
    )
    # --- START OF THE FIX ---
    allowed_origins = [
        "http://localhost:5173",  # Your Vite dev server
        "http://127.0.0.1:5173", # Another way to access the dev server
        # "https://your-deployed-frontend.com" # TODO: Add this when you deploy the frontend
    ]

    # Configure CORS with the specific origins and support for credentials (cookies)
    CORS(app, origins=allowed_origins, supports_credentials=True)

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