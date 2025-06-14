import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'a_default_secret_key_for_development')
    MONGO_URI = os.getenv('MONGO_URI')
    ABSTRACT_API_KEY = os.getenv('ABSTRACT_API_KEY')

    if not MONGO_URI or not ABSTRACT_API_KEY:
        raise ValueError("MONGO_URI and ABSTRACT_API_KEY must be set in the environment.")