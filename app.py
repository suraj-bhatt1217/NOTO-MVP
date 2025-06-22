"""
Refactored Noto MVP Flask Application
A modular, secure, and maintainable video summarization SaaS platform.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, session
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
import firebase_admin
from firebase_admin import credentials, firestore
import paypalrestsdk

# Import configuration and modules
from config import config
from blueprints.auth_routes import auth_bp
from blueprints.main_routes import create_main_blueprint
from blueprints.payment_routes import create_payment_blueprint
from blueprints.webhook_routes import create_webhook_blueprint

def create_app(config_name=None):
    """Application factory pattern for creating Flask app."""
    
    # Determine configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config.get(config_name, config['default']))
    
    # Initialize extensions
    CORS(app)
    csrf = CSRFProtect(app)
    
    # Configure logging
    configure_logging(app)
    
    # Initialize Firebase
    db = initialize_firebase(app)
    
    # Initialize PayPal
    initialize_paypal(app)
    
    # Register blueprints
    register_blueprints(app, db, csrf)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def configure_logging(app):
    """Configure application logging."""
    if not app.debug and not app.testing:
        # In serverless environments (like Vercel), use console logging instead of file logging
        if os.environ.get('VERCEL') or os.environ.get('FLASK_ENV') == 'production':
            # Configure console handler for production/serverless
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            app.logger.addHandler(console_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Noto MVP application startup (serverless)')
        else:
            # Local development - use file logging
            try:
                # Create logs directory if it doesn't exist
                if not os.path.exists('logs'):
                    os.mkdir('logs')
                
                # Configure file handler
                file_handler = RotatingFileHandler(
                    'logs/noto_mvp.log', 
                    maxBytes=10240000, 
                    backupCount=10
                )
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)
                
                app.logger.setLevel(logging.INFO)
                app.logger.info('Noto MVP application startup (local)')
            except OSError:
                # Fallback to console logging if file logging fails
                console_handler = logging.StreamHandler()
                console_handler.setLevel(logging.INFO)
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                app.logger.addHandler(console_handler)
                app.logger.setLevel(logging.INFO)
                app.logger.info('Noto MVP application startup (fallback to console)')
    
    # Configure console logging for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

def initialize_firebase(app):
    """Initialize Firebase Admin SDK."""
    try:
        # Check if Firebase is already initialized
        try:
            firebase_admin.get_app()
            app.logger.info("Firebase already initialized")
        except ValueError:
            # Initialize Firebase
            cred = credentials.Certificate(app.config['FIREBASE_CONFIG'])
            firebase_admin.initialize_app(cred)
            app.logger.info("Firebase initialized successfully")
        
        # Get Firestore client
        db = firestore.client()
        app.logger.info("Firestore client initialized")
        return db
        
    except Exception as e:
        app.logger.error(f"Failed to initialize Firebase: {str(e)}")
        raise

def initialize_paypal(app):
    """Initialize PayPal SDK."""
    try:
        paypal_config = {
            "mode": app.config['PAYPAL_MODE'],
            "client_id": app.config['PAYPAL_CLIENT_ID'],
            "client_secret": app.config['PAYPAL_CLIENT_SECRET']
        }
        
        paypalrestsdk.configure(paypal_config)
        
        app.logger.info(f"PayPal configured in {app.config['PAYPAL_MODE']} mode")
        
        # Validate PayPal configuration
        if (not app.config['PAYPAL_CLIENT_ID'] or 
            not app.config['PAYPAL_CLIENT_SECRET']):
            app.logger.warning("PayPal credentials not properly configured")
        
    except Exception as e:
        app.logger.error(f"Failed to initialize PayPal: {str(e)}")
        raise

def register_blueprints(app, db, csrf):
    """Register application blueprints and context processors."""
    # Main routes (no CSRF protection needed for these)
    main_bp = create_main_blueprint(db)
    app.register_blueprint(main_bp)
    
    # Auth routes (no CSRF protection needed for these)
    from auth import is_authenticated
    app.jinja_env.globals.update(is_authenticated=is_authenticated)
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Payment routes (CSRF protection needed)
    payment_bp = create_payment_blueprint(db)
    csrf.exempt(payment_bp)  # Exempt from CSRF since we're using our own token validation
    app.register_blueprint(payment_bp, url_prefix='/api')
    
    # Webhook routes (no CSRF protection needed for webhooks)
    webhook_bp = create_webhook_blueprint(db)
    app.register_blueprint(webhook_bp, url_prefix='/webhook')
    
    # Exempt certain routes from CSRF protection
    csrf.exempt(auth_bp)  # Firebase handles auth security
    
    # Add context processor for common template variables
    @app.context_processor
    def inject_template_vars():
        """Inject common variables into all templates."""
        from datetime import datetime
        from config import Config
        
        context = {
            'app_name': 'Noto',
            'current_year': datetime.now().year,
            'plans': Config.SUBSCRIPTION_PLANS,
            'is_authenticated': is_authenticated()
        }
        
        # Add user data if authenticated
        if is_authenticated():
            from flask import session
            from user_helpers import get_user_plan_data, format_plan_data
            
            user_id = session.get('user', {}).get('uid')
            if user_id:
                user_plan_data = get_user_plan_data(db, user_id)
                if user_plan_data:
                    context['plan_data'] = format_plan_data(user_plan_data, Config.SUBSCRIPTION_PLANS)
        
        return context
    
    app.logger.info("Blueprints and context processor registered successfully")

def register_error_handlers(app):
    """Register custom error handlers."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"404 error: {error}")
        return {"error": "Resource not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"500 error: {error}")
        return {"error": "Internal server error"}, 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f"403 error: {error}")
        return {"error": "Access forbidden"}, 403
    
    @app.errorhandler(400)
    def bad_request_error(error):
        app.logger.warning(f"400 error: {error}")
        return {"error": "Bad request"}, 400

# Create application instance
app = create_app()

# Debug route for environment checking (remove in production)
@app.route('/debug/env')
def debug_env():
    """Debug route to check environment variables (remove in production)."""
    if not app.debug:
        return {"error": "Debug mode disabled"}, 403
    
    return {
        'PAYPAL_CLIENT_ID': 'SET' if app.config.get('PAYPAL_CLIENT_ID') else 'NOT SET',
        'PAYPAL_CLIENT_SECRET': 'SET' if app.config.get('PAYPAL_CLIENT_SECRET') else 'NOT SET',
        'PAYPAL_MODE': app.config.get('PAYPAL_MODE', 'not set'),
        'OPENAI_API_KEY': 'SET' if app.config.get('OPENAI_API_KEY') else 'NOT SET',
        'FIREBASE_PROJECT_ID': 'SET' if app.config.get('FIREBASE_CONFIG', {}).get('project_id') else 'NOT SET'
    }

# For Vercel deployment
application = app

if __name__ == "__main__":
    app.run(debug=True)
