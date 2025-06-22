"""
Authentication routes blueprint for the Noto MVP application.
"""
import logging
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
import firebase_admin
from firebase_admin import auth as firebase_auth
from auth import auth_required
from utils import initialize_new_user

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login")
def login():
    """Render login page."""
    return render_template("login.html")

@auth_bp.route("/signup")
def signup():
    """Render signup page."""
    return render_template("signup.html")

@auth_bp.route("/forgot-password")
def reset_password():
    """Render forgot password page."""
    return render_template("forgot_password.html")

@auth_bp.route("/authorize", methods=["POST"])
def authorize():
    """Handle Firebase authentication and create session."""
    try:
        # Get the ID token from the request
        id_token = request.json.get("idToken")
        
        if not id_token:
            return jsonify({"error": "No ID token provided"}), 400

        # Verify the ID token
        decoded_token = firebase_auth.verify_id_token(id_token)
        uid = decoded_token["uid"]
        
        # Create session
        session["user"] = {
            "uid": uid,
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture")
        }
        
        # Make session permanent
        session.permanent = True
        
        logger.info(f"User authenticated: {uid}")
        
        return jsonify({
            "success": True,
            "message": "Authentication successful",
            "redirect_url": url_for("main.dashboard")
        })
        
    except firebase_admin.auth.InvalidIdTokenError:
        logger.warning("Invalid ID token provided")
        return jsonify({"error": "Invalid authentication token"}), 401
    except firebase_admin.auth.ExpiredIdTokenError:
        logger.warning("Expired ID token provided")
        return jsonify({"error": "Authentication token expired"}), 401
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({"error": "Authentication failed"}), 500

@auth_bp.route("/logout")
@auth_required
def logout():
    """Handle user logout."""
    user_id = session.get("user", {}).get("uid")
    session.clear()
    logger.info(f"User logged out: {user_id}")
    return redirect(url_for("main.home"))
