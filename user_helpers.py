"""
Helper functions for user and plan data operations.
"""
import logging
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)

def get_user_plan_data(db, user_id):
    """
    Fetch user and plan data from Firestore.
    
    Args:
        db: Firestore database instance
        user_id: ID of the user
        
    Returns:
        dict: Dictionary containing user and plan data
    """
    try:
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            logger.warning(f"User {user_id} not found")
            return None
            
        user_data = user_doc.to_dict()
        subscription = user_data.get("subscription", {})
        plan_type = subscription.get("plan", "free")
        usage_minutes = user_data.get("usage", {}).get("minutes_used_this_month", 0)
        
        return {
            "user_data": user_data,
            "subscription": subscription,
            "plan_type": plan_type,
            "usage_minutes": usage_minutes
        }
        
    except Exception as e:
        logger.error(f"Error fetching user plan data for {user_id}: {str(e)}")
        return None

def with_user_plan_data(db):
    """
    Decorator to inject user and plan data into route functions.
    
    Args:
        db: Firestore database instance
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = kwargs.get('user_id')
            if not user_id:
                return jsonify({"error": "User ID not provided"}), 400
                
            plan_data = get_user_plan_data(db, user_id)
            if not plan_data:
                return jsonify({"error": "User not found"}), 404
                
            kwargs['plan_data'] = plan_data
            return f(*args, **kwargs)
            
        return decorated_function
    return decorator

def format_plan_data(plan_data, plans_config):
    """
    Format plan data for template rendering.
    
    Args:
        plan_data: Dictionary containing user's plan data
        plans_config: Subscription plans configuration
        
    Returns:
        dict: Formatted plan data for templates
    """
    if not plan_data:
        return {
            "plan": "free",
            "status": "active",
            "current_period_end": None,
            "minutes_used": 0,
            "minutes_limit": plans_config["free"]["minutes_limit"],
            "percentage_used": 0,
            "next_billing_date": None,
            "recent_videos": []
        }
        
    plan_type = plan_data.get("plan_type", "free")
    usage_minutes = plan_data.get("usage_minutes", 0)
    plan_limit = plans_config.get(plan_type, {}).get("minutes_limit", 30)
    percentage_used = min(int((usage_minutes / plan_limit) * 100), 100) if plan_limit > 0 else 0
    
    return {
        "plan": plan_type,
        "status": plan_data.get("subscription", {}).get("status", "active"),
        "current_period_end": plan_data.get("subscription", {}).get("current_period_end"),
        "minutes_used": usage_minutes,
        "minutes_limit": plan_limit,
        "percentage_used": percentage_used,
        "next_billing_date": plan_data.get("subscription", {}).get("current_period_end", "N/A"),
        "recent_videos": []
    }
