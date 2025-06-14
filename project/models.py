from flask_login import UserMixin
from bson import ObjectId
import secrets

# This is a reference to the PyMongo database instance
# It will be initialized in __init__.py
db = None

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.name = user_data.get('name')
        self.email = user_data.get('email')
        self.password_hash = user_data.get('password_hash')
        self.api_key = user_data.get('api_key')

    @staticmethod
    def find_by_email(email):
        user_data = db.users.find_one({'email': email})
        return User(user_data) if user_data else None

    @staticmethod
    def find_by_id(user_id):
        try:
            user_data = db.users.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        except Exception:
            return None
            
    @staticmethod
    def find_by_api_key(api_key):
        user_data = db.users.find_one({'api_key': api_key})
        return User(user_data) if user_data else None

    @staticmethod
    def create(name, email, password_hash):
        # Generate a unique API key for the new user
        api_key = f"trk_{secrets.token_urlsafe(16)}"
        user_id = db.users.insert_one({
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'api_key': api_key
        }).inserted_id
        return str(user_id)

# You can add more models here for Campaigns, Links, etc. if needed
# For now, we'll manage them directly in the routes for simplicity.