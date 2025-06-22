"""
Authentication and authorization utilities for the Noto MVP application.
"""
import logging
from functools import wraps
from flask import session, redirect, url_for, jsonify
from config import Config

logger = logging.getLogger(__name__)

def auth_required(f):
    """Decorator for routes that require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            logger.warning("Unauthorized access attempt to protected route")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def plan_checker(db):
    """
    Decorator factory to check if user has enough minutes in their plan.
    Takes database instance as parameter to avoid circular imports.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("auth.login"))

            user_id = session["user"]["uid"]
            
            try:
                # Get user subscription and usage data
                user_ref = db.collection("users").document(user_id)
                user_doc = user_ref.get()

                if not user_doc.exists:
                    # Initialize new user with default free plan
                    from utils import initialize_new_user
                    initialize_new_user(db, user_id)
                    user_doc = user_ref.get()

                user_data = user_doc.to_dict()
                plan_type = user_data.get("subscription", {}).get("plan", "free")
                usage_minutes = user_data.get("usage", {}).get("minutes_used_this_month", 0)
                plan_limit = Config.SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]

                if usage_minutes >= plan_limit:
                    logger.warning(f"User {user_id} exceeded plan limit: {usage_minutes}/{plan_limit}")
                    return jsonify({
                        "error": "Plan limit exceeded",
                        "minutes_used": usage_minutes,
                        "plan_limit": plan_limit,
                        "message": "You have reached your monthly limit. Please upgrade your plan to continue.",
                    }), 403

                # Store user data in session for this request to avoid repeated DB calls
                session['_temp_user_data'] = user_data
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Error in plan_checker for user {user_id}: {str(e)}")
                return jsonify({"error": "Unable to verify plan limits"}), 500
            finally:
                # Clean up temporary session data
                session.pop('_temp_user_data', None)

        return decorated_function
    return decorator

def get_current_user_data():
    """Get current user data from session (if available from plan_checker)."""
    return session.get('_temp_user_data')

def is_authenticated():
    """Check if current user is authenticated."""
    return "user" in session

def get_current_user_id():
    """Get current user ID from session."""
    if is_authenticated():
        return session["user"]["uid"]
    return None
