"""
Payment processing module for the Noto MVP application.
Handles PayPal integration with enhanced security and error handling.
"""
import logging
import paypalrestsdk
from flask import url_for, session
from config import Config
from utils import update_user_subscription

logger = logging.getLogger(__name__)

class PaymentProcessor:
    """PayPal payment processor with enhanced security."""
    
    def __init__(self, db):
        self.db = db
        self._configure_paypal()
    
    def _configure_paypal(self):
        """Configure PayPal SDK."""
        try:
            paypalrestsdk.configure({
                "mode": Config.PAYPAL_MODE,
                "client_id": Config.PAYPAL_CLIENT_ID,
                "client_secret": Config.PAYPAL_CLIENT_SECRET
            })
            logger.info(f"PayPal configured in {Config.PAYPAL_MODE} mode")
        except Exception as e:
            logger.error(f"Failed to configure PayPal: {str(e)}")
            raise
    
    def create_payment(self, plan_id, user_id):
        """
        Create a PayPal payment for the specified plan.
        
        Args:
            plan_id (str): The subscription plan ID
            user_id (str): The user ID making the payment
            
        Returns:
            dict: Payment creation result with approval_url and payment_id
        """
        if plan_id not in Config.SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan ID: {plan_id}")
        
        if plan_id == "free":
            # Handle free plan subscription
            update_user_subscription(self.db, user_id, "free", None)
            return {
                "success": True,
                "message": "Subscribed to Free plan",
                "is_free": True
            }
        
        plan_data = Config.SUBSCRIPTION_PLANS[plan_id]
        
        try:
            # Store payment intent in database for verification
            payment_intent = {
                "user_id": user_id,
                "plan_id": plan_id,
                "amount": plan_data["price"],
                "currency": plan_data["currency"],
                "created_at": paypalrestsdk.util.get_current_time(),
                "status": "pending"
            }
            
            # Create PayPal payment
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": url_for('main.pricing', _external=True) + f"?paypal_status=success&plan_id={plan_id}",
                    "cancel_url": url_for('main.pricing', _external=True) + "?paypal_status=cancelled"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": plan_data["name"],
                            "sku": plan_id,
                            "price": "{:.2f}".format(plan_data["price"] / 100.0),
                            "currency": plan_data["currency"],
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": "{:.2f}".format(plan_data["price"] / 100.0),
                        "currency": plan_data["currency"]
                    },
                    "description": f"Subscription to {plan_data['name']}",
                    "custom": user_id  # Store user_id for verification
                }]
            })
            
            if payment.create():
                # Store payment intent in database
                payment_intent["payment_id"] = payment.id
                self.db.collection("payment_intents").document(payment.id).set(payment_intent)
                
                approval_url = next((link.href for link in payment.links if link.rel == "approval_url"), None)
                if approval_url:
                    logger.info(f"Payment created for user {user_id}, plan {plan_id}: {payment.id}")
                    return {
                        "success": True,
                        "approval_url": approval_url,
                        "payment_id": payment.id
                    }
                else:
                    logger.error(f"No approval URL found for payment {payment.id}")
                    raise Exception("Could not get PayPal approval URL")
            else:
                logger.error(f"PayPal payment creation failed: {payment.error}")
                raise Exception(f"PayPal payment creation failed: {self._format_paypal_error(payment.error)}")
                
        except Exception as e:
            logger.error(f"Error creating payment for user {user_id}: {str(e)}")
            raise
    
    def verify_payment(self, payment_id, payer_id, user_id):
        """
        Verify and execute PayPal payment with enhanced security.
        
        Args:
            payment_id (str): PayPal payment ID
            payer_id (str): PayPal payer ID
            user_id (str): User ID from session
            
        Returns:
            dict: Payment verification result
        """
        try:
            # Retrieve payment intent from database
            intent_doc = self.db.collection("payment_intents").document(payment_id).get()
            if not intent_doc.exists:
                logger.warning(f"Payment intent not found: {payment_id}")
                raise Exception("Payment intent not found or expired")
            
            intent_data = intent_doc.to_dict()
            
            # Verify user matches the payment intent
            if intent_data.get("user_id") != user_id:
                logger.warning(f"User ID mismatch for payment {payment_id}: {user_id} vs {intent_data.get('user_id')}")
                raise Exception("Payment verification failed: user mismatch")
            
            # Verify payment hasn't been processed already
            if intent_data.get("status") != "pending":
                logger.warning(f"Payment {payment_id} already processed with status: {intent_data.get('status')}")
                raise Exception("Payment already processed")
            
            # Find and execute PayPal payment
            payment = paypalrestsdk.Payment.find(payment_id)
            
            # Verify payment details match our intent
            if not self._verify_payment_details(payment, intent_data):
                logger.error(f"Payment details verification failed for {payment_id}")
                raise Exception("Payment details verification failed")
            
            if payment.execute({"payer_id": payer_id}):
                # Update user subscription
                plan_id = intent_data["plan_id"]
                update_user_subscription(self.db, user_id, plan_id, payment.id)
                
                # Mark payment intent as completed
                self.db.collection("payment_intents").document(payment_id).update({
                    "status": "completed",
                    "completed_at": paypalrestsdk.util.get_current_time(),
                    "payer_id": payer_id
                })
                
                logger.info(f"Payment verified and executed for user {user_id}: {payment_id}")
                
                return {
                    "success": True,
                    "message": f'Payment successful. Subscribed to {Config.SUBSCRIPTION_PLANS[plan_id]["name"]}.',
                    "payment_id": payment.id,
                    "plan_id": plan_id
                }
            else:
                logger.error(f"PayPal payment execution failed: {payment.error}")
                # Mark payment intent as failed
                self.db.collection("payment_intents").document(payment_id).update({
                    "status": "failed",
                    "error": str(payment.error),
                    "failed_at": paypalrestsdk.util.get_current_time()
                })
                raise Exception(f"PayPal payment execution failed: {self._format_paypal_error(payment.error)}")
                
        except paypalrestsdk.exceptions.ResourceNotFound:
            logger.error(f"PayPal payment not found: {payment_id}")
            raise Exception("PayPal payment not found")
        except paypalrestsdk.exceptions.ConnectionError as ce:
            logger.error(f"PayPal connection error: {str(ce)}")
            raise Exception("Could not connect to PayPal. Please try again.")
        except Exception as e:
            logger.error(f"Payment verification error for {payment_id}: {str(e)}")
            raise
    
    def _verify_payment_details(self, payment, intent_data):
        """Verify payment details match our stored intent."""
        try:
            if not payment.transactions:
                return False
            
            transaction = payment.transactions[0]
            expected_amount = "{:.2f}".format(intent_data["amount"] / 100.0)
            actual_amount = transaction.amount.total
            
            # Verify amount and currency
            if (actual_amount != expected_amount or 
                transaction.amount.currency != intent_data["currency"]):
                logger.warning(f"Payment amount/currency mismatch: expected {expected_amount} {intent_data['currency']}, got {actual_amount} {transaction.amount.currency}")
                return False
            
            # Verify custom field contains correct user_id
            if transaction.custom != intent_data["user_id"]:
                logger.warning(f"Payment user_id mismatch in custom field: expected {intent_data['user_id']}, got {transaction.custom}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying payment details: {str(e)}")
            return False
    
    def _format_paypal_error(self, error):
        """Format PayPal error for user-friendly display."""
        if not error:
            return "Unknown PayPal error"
        
        error_message = error.get('message', 'Unknown PayPal error')
        error_details = error.get('details', [])
        
        if error_details:
            detail_messages = [d.get('issue', '') for d in error_details if d.get('issue')]
            if detail_messages:
                error_message += " - " + ", ".join(detail_messages)
        
        return error_message
    
    def get_plan_details(self, plan_id):
        """Get subscription plan details."""
        if plan_id not in Config.SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan ID: {plan_id}")
        
        return Config.SUBSCRIPTION_PLANS[plan_id]
