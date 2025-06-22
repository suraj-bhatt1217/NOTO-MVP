"""
Payment routes blueprint for the Noto MVP application.
"""
import logging
from flask import Blueprint, request, jsonify
from auth import auth_required, get_current_user_id
from payment import PaymentProcessor
from config import Config

logger = logging.getLogger(__name__)

def create_payment_blueprint(db):
    """Factory function to create payment blueprint with database dependency."""
    payment_bp = Blueprint('payment', __name__)
    payment_processor = PaymentProcessor(db)

    @payment_bp.route("/api/create-subscription", methods=["POST"])
    @auth_required
    def create_subscription():
        """Create a subscription payment."""
        try:
            data = request.json
            plan_id = data.get("plan_id")
            
            if not plan_id:
                return jsonify({"error": "Plan ID is required"}), 400
            
            if plan_id not in Config.SUBSCRIPTION_PLANS:
                return jsonify({"error": "Invalid plan selected"}), 400
            
            user_id = get_current_user_id()
            
            result = payment_processor.create_payment(plan_id, user_id)
            
            if result.get("is_free"):
                return jsonify(result)
            
            return jsonify({
                "approval_url": result["approval_url"],
                "payment_id": result["payment_id"]
            })
            
        except ValueError as e:
            logger.warning(f"Invalid payment request: {str(e)}")
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Error creating subscription: {str(e)}")
            return jsonify({"error": "Failed to create subscription"}), 500

    @payment_bp.route("/api/verify-payment", methods=["POST"])
    @auth_required
    def verify_payment():
        """Verify and execute PayPal payment."""
        try:
            data = request.json
            payment_id = data.get("payment_id")
            payer_id = data.get("payer_id")
            
            if not all([payment_id, payer_id]):
                return jsonify({"error": "Missing payment verification details"}), 400
            
            user_id = get_current_user_id()
            
            result = payment_processor.verify_payment(payment_id, payer_id, user_id)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return jsonify({"error": str(e)}), 400

    @payment_bp.route("/api/get-plan-details/<plan_id>")
    @auth_required
    def get_plan_details(plan_id):
        """Get subscription plan details."""
        try:
            plan_details = payment_processor.get_plan_details(plan_id)
            return jsonify(plan_details)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Error getting plan details: {str(e)}")
            return jsonify({"error": "Failed to get plan details"}), 500

    return payment_bp
