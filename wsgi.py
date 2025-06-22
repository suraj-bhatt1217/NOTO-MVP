"""
WSGI entry point for Vercel deployment.
"""
import os
from app import create_app

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

# Create the application instance
application = create_app('production')

# For compatibility with different WSGI servers
app = application

if __name__ == "__main__":
    application.run()
