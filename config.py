"""
Configuration settings for the Noto MVP application.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.getenv("SECRET_KEY")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    # Session Configuration
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    
    # Bright Data Configuration
    BRIGHT_DATA_AUTH_TOKEN = os.getenv("BRIGHT_DATA_AUTH_TOKEN")
    BRIGHT_DATA_DATASET_ID = os.getenv("BRIGHT_DATA_DATASET_ID", "gd_lk56epmy2i5g7lzu0k")
    
    # PayPal Configuration
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
    PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")
    
    # Firebase Configuration
    FIREBASE_CONFIG = {
        "type": "service_account",
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
        "universe_domain": "googleapis.com",
    }
    
    # Subscription Plans Configuration
    SUBSCRIPTION_PLANS = {
        "free": {
            "name": "Free Plan",
            "minutes_limit": 30,
            "price": 0,
            "currency": "USD",
            "features": ["Basic Summaries", "Limited to 30 min/month"],
        },
        "pro": {
            "name": "Pro Plan",
            "minutes_limit": 100,
            "price": 999,  # $9.99 in cents
            "currency": "USD",
            "features": ["Premium Summaries", "100 min/month", "Unlimited Videos"],
        },
        "elite": {
            "name": "Elite Plan",
            "minutes_limit": 300,
            "price": 2999,  # $29.99 in cents
            "currency": "USD",
            "features": [
                "Premium Summaries",
                "300 min/month",
                "Priority Processing",
                "Premium Support",
            ],
        },
    }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
