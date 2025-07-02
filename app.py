from flask import (
    Flask,
    redirect,
    render_template,
    request,
    make_response,
    session,
    abort,
    jsonify,
    url_for,
)
import secrets
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import timedelta, datetime
import os
import re
from dotenv import load_dotenv
from services.bright_data import BrightDataService

# Initialize BrightData service
bright_data_service = BrightDataService()
import openai
import razorpay
import json
import hmac
import hashlib
import requests
from flask_cors import CORS
from dateutil.relativedelta import relativedelta

load_dotenv()


app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY")

# Configure session cookie settings
app.config["SESSION_COOKIE_SECURE"] = True  # Ensure cookies are sent over HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access to cookies
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    days=1
)  # Adjust session expiration as needed
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Can be 'Strict', 'Lax', or 'None'

# API Keys and Configuration
openai.api_key = os.getenv("OPENAI_API_KEY")

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Firebase Admin SDK setup
firebase_credentials = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": (os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n")),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
    "universe_domain": "googleapis.com",
}

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Define subscription plans
SUBSCRIPTION_PLANS = {
    "free": {
        "name": "Free Plan",
        "minutes_limit": 30,  # 30 minutes per month
        "price": 0,
        "currency": "USD",
        "features": ["Basic Summaries", "Limited to 30 min/month"],
    },
    "pro": {
        "name": "Pro Plan",
        "minutes_limit": 100,  # 100 minutes per month
        "price": 1499,  # $14.99
        "currency": "USD",
        "features": ["Premium Summaries", "100 min/month", "Unlimited Videos"],
    },
    "elite": {
        "name": "Elite Plan",
        "minutes_limit": 300,  # 300 minutes per month
        "price": 2999,  # $29.99
        "currency": "USD",
        "features": [
            "Premium Summaries",
            "300 min/month",
            "Priority Processing",
            "Premium Support",
        ],
    },
}


########################################
""" Authentication and Authorization """


# Decorator for routes that require authentication
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if "user" not in session:
            return redirect(url_for("login"))

        else:
            return f(*args, **kwargs)

    return decorated_function


# Decorator to check if user has enough minutes in their plan
def plan_checker(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))

        user_id = session["user"]["uid"]
        # Get user subscription and usage data
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # Set up default free plan for new users
            initialize_new_user(user_id)
            user_doc = user_ref.get()

        user_data = user_doc.to_dict()
        plan_type = user_data.get("subscription", {}).get("plan", "free")
        usage_minutes = user_data.get("usage", {}).get("minutes_used_this_month", 0)
        plan_limit = SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]

        if usage_minutes >= plan_limit:
            return (
                jsonify(
                    {
                        "error": "Plan limit exceeded",
                        "minutes_used": usage_minutes,
                        "plan_limit": plan_limit,
                        "message": "You have reached your monthly limit. Please upgrade your plan to continue.",
                    }
                ),
                403,
            )

        # Continue with the function
        return f(*args, **kwargs)

    return decorated_function


# Function to initialize a new user with default settings
def initialize_new_user(user_id):
    today = datetime.now()
    next_month = today + relativedelta(
        months=1, day=1, hour=0, minute=0, second=0, microsecond=0
    )

    user_data = {
        "subscription": {
            "plan": "free",
            "start_date": today,
            "next_billing_date": next_month,
            "status": "active",
        },
        "usage": {
            "minutes_used_this_month": 0,
            "reset_date": next_month,
            "video_history": [],
        },
        "profile": {
            "created_at": today,
            "email": session.get("user", {}).get("email", "unknown"),
        },
    }

    db.collection("users").document(user_id).set(user_data)


@app.route("/")
def home():
    # If user is already logged in, redirect to dashboard
    if "user" in session:
        return redirect(url_for("dashboard"))
    # Otherwise show the home page for non-authenticated users
    return render_template("home.html")


@app.route("/auth", methods=["POST"])
def authorize():
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        return "Unauthorized", 401

    token = token[7:]  # Strip off 'Bearer ' to get the actual token

    try:
        decoded_token = auth.verify_id_token(
            token, check_revoked=True, clock_skew_seconds=60
        )  # Validate token here
        session["user"] = decoded_token  # Add user to session
        return redirect(url_for("dashboard"))

    except:
        return "Unauthorized", 401


@app.route("/login")
def login():
    if "user" in session:
        return redirect(url_for("dashboard"))
    else:
        return render_template("login.html")


@app.route("/signup")
def signup():
    if "user" in session:
        return redirect(url_for("dashboard"))
    else:
        return render_template("signup.html")


@app.route("/terms")
def terms():
    is_authenticated = "user" in session
    
    # Default values for non-authenticated users
    plan_data = {"plan": "free"}
    
    # If user is authenticated, get their plan data
    if is_authenticated:
        user_id = session["user"]["uid"]
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            plan_data = user_data.get("subscription", {"plan": "free"})
    
    return render_template(
        "terms.html", 
        is_authenticated=is_authenticated,
        plan_data=plan_data,
        plans=SUBSCRIPTION_PLANS
    )


@app.route("/privacy")
def privacy():
    is_authenticated = "user" in session
    
    # Default values for non-authenticated users
    plan_data = {"plan": "free"}
    
    # If user is authenticated, get their plan data
    if is_authenticated:
        user_id = session["user"]["uid"]
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            plan_data = user_data.get("subscription", {"plan": "free"})
    
    return render_template(
        "privacy.html", 
        is_authenticated=is_authenticated,
        plan_data=plan_data,
        plans=SUBSCRIPTION_PLANS
    )


@app.route("/reset-password")
def reset_password():
    if "user" in session:
        return redirect(url_for("dashboard"))
    else:
        return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.pop("user", None)  # Remove the user from session
    response = make_response(redirect(url_for("login")))
    response.set_cookie("session", "", expires=0)  # Optionally clear the session cookie
    return response


##############################################
""" Private Routes (Require authorization) """


@app.route("/dashboard")
@auth_required
def dashboard():
    user_id = session["user"]["uid"]
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        initialize_new_user(user_id)
        user_doc = user_ref.get()

    user_data = user_doc.to_dict()

    # Format the data for the template
    minutes_used = user_data.get("usage", {}).get("minutes_used_this_month", 0)
    plan_type = user_data.get("subscription", {}).get("plan", "free")
    minutes_limit = SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]
    
    # Calculate percentage used - ensure it's a valid number to prevent display issues
    percentage_used = 0
    if minutes_limit > 0:
        percentage_used = round((minutes_used / minutes_limit) * 100, 1)
    
    plan_data = {
        "plan": plan_type,
        "minutes_used": minutes_used,
        "minutes_limit": minutes_limit,
        "percentage_used": percentage_used,
        "next_billing_date": user_data.get("subscription", {})
        .get("next_billing_date", datetime.now())
        .strftime("%B %d, %Y"),
        "recent_videos": user_data.get("usage", {}).get("video_history", [])[
            :5
        ],  # Get last 5 videos
    }

    return render_template(
        "dashboard.html",
        user_data=user_data,
        plan_data=plan_data,
        plans=SUBSCRIPTION_PLANS,
    )


@app.route("/pricing")
def pricing():
    # Initialize default values for non-logged in users
    current_plan = "free"
    plan_data = {"plan": "free"}
    is_authenticated = "user" in session

    # If user is logged in, get their plan data
    if is_authenticated:
        user_id = session["user"]["uid"]
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            initialize_new_user(user_id)
            user_doc = user_ref.get()

        user_data = user_doc.to_dict()
        current_plan = user_data.get("subscription", {}).get("plan", "free")
        plan_data = user_data.get("subscription", {"plan": "free"})

    return render_template(
        "pricing.html",
        plans=SUBSCRIPTION_PLANS,
        current_plan=current_plan,
        plan_data=plan_data,
        is_authenticated=is_authenticated,
    )


@app.route("/api/extract-video-info", methods=["POST"])
@auth_required
def extract_video_info():
    data = request.json
    video_url = data.get("video_url", "")

    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        # Get video details from YouTube API
        api_key = os.getenv("YOUTUBE_API_KEY")
        video_details_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=snippet,contentDetails"
        response = requests.get(video_details_url)
        video_data = response.json()

        if not video_data.get("items"):
            return jsonify({"error": "Video not found or unavailable"}), 404

        video_info = video_data["items"][0]
        duration = parse_duration(video_info["contentDetails"]["duration"])

        return jsonify(
            {
                "video_id": video_id,
                "title": video_info["snippet"]["title"],
                "thumbnail": video_info["snippet"]["thumbnails"]["high"]["url"],
                "duration_seconds": duration,
                "duration_minutes": round(duration / 60, 2),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/user-usage")
@auth_required
def get_user_usage():
    user_id = session["user"]["uid"]
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        initialize_new_user(user_id)
        user_doc = user_ref.get()

    user_data = user_doc.to_dict()

    usage_data = {
        "plan": user_data.get("subscription", {}).get("plan", "free"),
        "minutes_used": user_data.get("usage", {}).get("minutes_used_this_month", 0),
        "minutes_limit": SUBSCRIPTION_PLANS[
            user_data.get("subscription", {}).get("plan", "free")
        ]["minutes_limit"],
        "next_billing_date": user_data.get("subscription", {})
        .get("next_billing_date", datetime.now())
        .strftime("%B %d, %Y"),
        "video_count": len(user_data.get("usage", {}).get("video_history", [])),
        "percentage_used": round(
            (
                user_data.get("usage", {}).get("minutes_used_this_month", 0)
                / SUBSCRIPTION_PLANS[
                    user_data.get("subscription", {}).get("plan", "free")
                ]["minutes_limit"]
            )
            * 100,
            1,
        ),
    }

    return jsonify(usage_data)


@app.route("/api/recent-videos")
@auth_required
def get_recent_videos():
    user_id = session["user"]["uid"]
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return jsonify([]), 200

    user_data = user_doc.to_dict()
    video_history = user_data.get("usage", {}).get("video_history", [])

    # Return the 10 most recent videos
    return jsonify(video_history[:10])


# Razorpay Integration
@app.route("/api/create-subscription", methods=["POST"])
@auth_required
def create_subscription():
    data = request.json
    plan_id = data.get("plan_id")
    user_country = request.headers.get('X-User-Country', 'US')  # Get user's country from frontend

    if not plan_id or plan_id not in SUBSCRIPTION_PLANS:
        return jsonify({"error": "Invalid plan selected"}), 400

    if plan_id == "free":
        # Handle free plan subscription
        user_id = session["user"]["uid"]
        update_user_subscription(user_id, "free", None)
        return jsonify({"success": True, "message": "Subscribed to Free plan"})

    plan_data = SUBSCRIPTION_PLANS[plan_id]
    user_id = session["user"]["uid"]
    user_email = session["user"].get("email", "customer@example.com")

    try:
        # For Indian users, convert to INR for Razorpay
        is_indian_user = user_country.upper() == 'IN'
        
        if is_indian_user:
            # Convert USD to INR (1 USD = 83.33 INR as an example)
            conversion_rate = 83.33
            order_amount = int(plan_data["price"] * conversion_rate)  # Convert to paise
            order_currency = "INR"
        else:
            order_amount = plan_data["price"]  # amount in paise (USD)
            order_currency = plan_data["currency"]
            
        order_receipt = f"order_rcptid_{secrets.token_hex(6)}"
        notes = {"user_id": user_id, "plan_id": plan_id, "original_currency": "USD", "original_amount": plan_data["price"]}

        order = razorpay_client.order.create(
            {
                "amount": order_amount,
                "currency": order_currency,
                "receipt": order_receipt,
                "notes": notes,
            }
        )

        # Always return display amount in USD
        display_amount = plan_data["price"] / 100  # Convert to dollars

        return jsonify(
            {
                "order_id": order["id"],
                "amount": order_amount,
                "currency": order_currency,
                "display_amount": display_amount,
                "display_currency": "USD",
                "key_id": RAZORPAY_KEY_ID,
                "product_name": plan_data["name"],
                "description": f"Subscription to {plan_data['name']}",
                "user_info": {
                    "name": session["user"].get("name", "Customer"),
                    "email": user_email,
                    "contact": session["user"].get("phoneNumber", ""),
                },
                "is_indian_user": is_indian_user
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/verify-payment", methods=["POST"])
@auth_required
def verify_payment():
    data = request.json
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_signature = data.get("razorpay_signature")
    plan_id = data.get("plan_id")

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature, plan_id]):
        return jsonify({"error": "Missing payment verification details"}), 400

    try:
        # Verify the payment signature
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        # Update the user's subscription
        user_id = session["user"]["uid"]
        update_user_subscription(user_id, plan_id, razorpay_payment_id)

        return jsonify(
            {
                "success": True,
                "message": f'Payment verified. Subscribed to {SUBSCRIPTION_PLANS[plan_id]["name"]}.',
            }
        )

    except razorpay.errors.SignatureVerificationError:
        return jsonify({"error": "Invalid payment signature"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/my-videos")
@auth_required
def my_videos():
    user_id = session["user"]["uid"]
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        initialize_new_user(user_id)
        user_doc = user_ref.get()

    user_data = user_doc.to_dict()
    video_history = user_data.get("usage", {}).get("video_history", [])
    plan_data = user_data.get("subscription", {"plan": "free"})

    return render_template(
        "my_videos.html",
        videos=video_history,
        plan_data=plan_data,
        plans=SUBSCRIPTION_PLANS,
    )


@app.route("/api/video-details/<video_id>")
@auth_required
def get_video_details(video_id):
    user_id = session["user"]["uid"]
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404

    user_data = user_doc.to_dict()
    video_history = user_data.get("usage", {}).get("video_history", [])

    for video in video_history:
        if video.get("video_id") == video_id:
            return jsonify(video)

    return jsonify({"error": "Video not found in user history"}), 404


import asyncio
import traceback

@app.route("/summarize", methods=["POST"])
@auth_required
@plan_checker
def summarize_video():
    """Handle video summarization"""
    print("\n=== /summarize endpoint called ===")
    print(f"Request data: {request.get_data()}")
    
    try:
        data = request.get_json()
        video_url = data.get("video_url")
        print(f"Processing video URL: {video_url}")
        
        if not video_url:
            print("Error: No video URL provided")
            return jsonify({"error": "Video URL is required"}), 400
            
        # Get user info
        user_id = session["user"]["uid"]
        print(f"Processing request for user: {user_id}")
        
        # Run the async function
        return asyncio.run(process_video_summary(video_url, user_id))
        
    except Exception as e:
        error_msg = f"Error in summarize_video: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return jsonify({"error": "An error occurred while processing your request"}), 500

async def process_video_summary(video_url, user_id):
    """Async function to process video summary with detailed logging"""
    print(f"\n--- Starting process_video_summary ---")
    print(f"Video URL: {video_url}")
    print(f"User ID: {user_id}")
    
    try:
        # Get user data (synchronous operation)
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()  # This is synchronous
        
        if not user_doc.exists:
            print(f"Error: User {user_id} not found")
            return jsonify({"error": "User not found"}), 404
            
        user_data = user_doc.to_dict()
        print(f"User data retrieved - Plan: {user_data.get('subscription', {}).get('plan', 'free')}")
        
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            print(f"Error: Could not extract video ID from URL: {video_url}")
            return jsonify({"error": "Invalid YouTube URL"}), 400
            
        print(f"Extracted video ID: {video_id}")
        
        # Check if we already have this video in progress/completed
        video_ref = db.collection("videos").document(video_id)
        video_doc = video_ref.get()  # This is synchronous
        
        if video_doc.exists:
            video_data = video_doc.to_dict()
            print(f"Found existing video data: {video_data}")
            
            if video_data.get('status') == 'completed':
                print("Video already processed, returning existing summary")
                return jsonify({
                    "status": "completed",
                    "video_id": video_id,
                    "summary": video_data.get('summary')
                })
            elif video_data.get('status') == 'processing':
                print("Video is already being processed")
                return jsonify({
                    "status": "processing",
                    "video_id": video_id,
                    "message": "Video is being processed. Please check back soon!"
                })
        
        # Check user's plan limits
        plan_type = user_data.get("subscription", {}).get("plan", "free")
        usage_minutes = user_data.get("usage", {}).get("minutes_used_this_month", 0)
        plan_limit = SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]
        
        print(f"Plan check - Type: {plan_type}, Used: {usage_minutes}min, Limit: {plan_limit}min")
        
        if usage_minutes >= plan_limit:
            print("Error: User has exceeded plan limit")
            return jsonify({
                "error": "Plan limit exceeded",
                "message": "You've reached your monthly minute limit. Please upgrade your plan."
            }), 403
        
        # Mark video as processing
        print("Marking video as processing in database...")
        video_ref.set({
            'status': 'processing',
            'created_at': firestore.SERVER_TIMESTAMP,
            'user_id': user_id,
            'video_url': f"https://www.youtube.com/watch?v={video_id}",
            'title': 'Processing...',
            'channel': 'Processing...',
            'thumbnail': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        }, merge=True)
        
        # Trigger transcript extraction
        print("Starting transcript extraction...")
        transcript, message = await get_video_transcript(video_id)
        
        if transcript:
            # This branch shouldn't normally be hit with Bright Data
            print("Got transcript immediately (unexpected with Bright Data)")
            summary = await generate_summary(
                transcript,
                plan_type,
                "Video Title",
                "Channel Name"
            )
            
            # Update video in database
            print("Updating video with completed summary...")
            video_data = {
                'status': 'completed',
                'summary': summary,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'title': "Video Title",
                'channel': "Channel Name"
            }
            db.collection("videos").document(video_id).set(video_data, merge=True)
            
            return jsonify({
                "status": "success",
                "video_id": video_id,
                "summary": summary
            })
        
        return jsonify({
            "status": "processing",
            "message": message or "Video is being processed. You'll be notified when it's ready."
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/webhooks/brightdata", methods=["POST"])
async def bright_data_webhook():
    """Handle incoming webhooks from Bright Data"""
    try:
        # Verify webhook signature if needed
        auth_header = request.headers.get('Authorization')
        expected_auth = f"Bearer {os.getenv('WEBHOOK_AUTH_SECRET')}"
        
        if auth_header != expected_auth:
            logger.warning("Invalid webhook signature")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
            
        # Parse and validate the webhook data
        payload = request.get_json()
        parsed_data = BrightDataService.parse_webhook_data(payload)
        
        if not parsed_data['valid']:
            logger.error(f"Invalid webhook data: {parsed_data.get('error')}")
            return jsonify({"status": "error", "message": "Invalid data"}), 400
            
        video_id = parsed_data['video_id']
        
        # Update video in database
        video_data = {
            'title': parsed_data['title'],
            'video_length': parsed_data['video_length'],
            'thumbnail_url': parsed_data['thumbnail_url'],
            'published_at': parsed_data['published_at'],
            'channel_name': parsed_data['channel_name'],
            'channel_avatar': parsed_data['channel_avatar'],
            'channel_url': parsed_data['channel_url'],
            'view_count': parsed_data['view_count'],
            'like_count': parsed_data['like_count'],
            'subscriber_count': parsed_data['subscriber_count'],
            'transcript': parsed_data['transcript'],
            'quality': parsed_data['quality'],
            'description': parsed_data['description'],
            'status': 'completed',
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        # Get the video document to find the user who requested it
        video_doc = db.collection("videos").document(video_id).get()
        if video_doc.exists:
            video_data['user_id'] = video_doc.to_dict().get('user_id')
        
        # Save to database
        db.collection("videos").document(video_id).set(video_data, merge=True)
        
        logger.info(f"Successfully processed webhook for video: {video_id}")
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


############################
""" Helper functions """


# Function to extract YouTube video ID from URL
def extract_video_id(url):
    # Regular expressions for different YouTube URL formats
    youtube_regex = (
        r"(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/"
        r"(watch\?v=|embed/|v/|shorts/|.+\?v=)?([^&=%\?]{11})"
    )
    youtube_match = re.match(youtube_regex, url)
    return youtube_match.group(6) if youtube_match else None


# Get video transcript
async def get_video_transcript(video_id):
    """Get video transcript using Bright Data
    Returns:
        tuple: (transcript_text, status_message)
    """
    try:
        # First check if we already have this video in our database
        video_ref = db.collection("videos").document(video_id)
        video_doc = video_ref.get()
        
        if video_doc.exists and "transcript" in video_doc.to_dict():
            # Return existing transcript if available
            return video_doc.to_dict()["transcript"], "Transcript retrieved from cache"
            
        # If not in DB, trigger Bright Data extraction
        result = await bright_data_service.trigger_transcript_extraction(video_id)
        if not result.get('success'):
            logger.error(f"Failed to trigger extraction: {result.get('error')}")
            return None, "Failed to start transcript extraction"
            
        return None, "Transcript is being processed. Please try again in a moment."
        
    except Exception as e:
        logger.error(f"Error in get_video_transcript: {str(e)}")
        return None, f"Error processing transcript: {str(e)}"


# Generate summary from transcript
def generate_summary(transcript, plan_type, title, channel):
    # Different summary types based on subscription plan
    if plan_type == "free":
        system_prompt = """You are an AI assistant that creates comprehensive summaries of YouTube video transcripts.
        Create a thorough summary that covers all important points in the transcript.
        Don't omit critical information, even for longer videos.
        Format your response with clear sections and good readability."""
        max_tokens = 3000  # Increased token count for free tier
    elif plan_type == "pro":
        system_prompt = """You are an AI assistant that creates premium structured summaries of YouTube video transcripts.
        Format your response with these sections:
        1. SUMMARY: A thorough overview of the video content
        2. KEY POINTS: Comprehensive bullet points of the important information
        3. INSIGHTS: Notable observations or takeaways
        4. ACTIONABLE TIPS: Practical advice from the video
        5. DETAILED NOTES: Section-by-section breakdown of content
        Use markdown formatting for better readability."""
        max_tokens = 4000  # Increased token count for pro tier
    else:  # 'elite'
        system_prompt = """You are an AI assistant that creates enterprise-grade summaries of YouTube video transcripts.
        Format your response with these sections:
        1. EXECUTIVE SUMMARY: A concise overview for quick understanding
        2. COMPREHENSIVE BREAKDOWN: Detailed coverage of all major topics
        3. KEY POINTS: Thorough bullet points of all important information
        4. INSIGHTS & ANALYSIS: Deep observations and contextual analysis
        5. ACTIONABLE TAKEAWAYS: Practical advice organized by relevance
        6. Q&A SECTION: Anticipated questions and answers based on content
        7. RELATED RESOURCES: Suggestions for further information (if mentioned)
        Use markdown formatting for optimal readability."""
        max_tokens = 6000  # Significantly increased token count for elite tier

    # Process transcript in chunks if it's too long
    def chunk_transcript(text, chunk_size=12000, overlap=2000):
        """Split transcript into overlapping chunks to preserve context."""
        if len(text) <= chunk_size:
            return [text]
            
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to find a sentence break to avoid cutting mid-sentence
            if end < len(text):
                sentence_breaks = ['.', '!', '?', '\n']
                for i in range(min(500, end - start), 0, -1):  # Look back up to 500 chars
                    if text[end - i] in sentence_breaks:
                        end = end - i + 1  # Include the period
                        break
            
            chunks.append(text[start:end])
            start = end - overlap  # Create overlap between chunks
            
        return chunks

    # Process transcript in chunks if needed
    transcript_chunks = chunk_transcript(transcript)
    
    # For single chunks or free tier, process directly
    if len(transcript_chunks) == 1 or plan_type == "free":
        prompt = f"Video Title: {title}\nChannel: {channel}\n\nTranscript: {transcript_chunks[0]}"
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o" if plan_type != "free" else "gpt-4o-mini",  # Use full GPT-4o for paid tiers
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.5,
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Error generating summary. Please try again later."
    
    # For longer transcripts on paid tiers, use a multi-pass approach
    else:
        # First pass: Generate summaries for each chunk
        chunk_summaries = []
        chunk_system_prompt = """Summarize this portion of a transcript comprehensively.
        Don't conclude or wrap up - this is just one part of a longer transcript.
        Maintain all key information, including specific details, numbers, and technical terms."""
        
        for i, chunk in enumerate(transcript_chunks):
            try:
                chunk_prompt = f"Video Title: {title}\nChannel: {channel}\n\nThis is part {i+1} of {len(transcript_chunks)} of the transcript:\n\n{chunk}"
                
                response = openai.chat.completions.create(
                    model="gpt-4o",  # Use full GPT-4o for chunk processing
                    messages=[
                        {"role": "system", "content": chunk_system_prompt},
                        {"role": "user", "content": chunk_prompt},
                    ],
                    max_tokens=4000,
                    temperature=0.3,  # Lower temperature for more factual intermediate summaries
                )
                
                chunk_summaries.append(response.choices[0].message.content)
            except Exception as e:
                print(f"Error processing chunk {i+1}: {e}")
                chunk_summaries.append(f"[Error processing this section of the transcript: {str(e)}]")
        
        # Second pass: Combine the summaries into a final, structured result
        combined_summary = "\n\n---\n\n".join(chunk_summaries)
        
        final_prompt = f"Video Title: {title}\nChannel: {channel}\n\nBelow are summaries of different sections of the transcript. Please create a cohesive final summary according to the specified format:\n\n{combined_summary}"
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",  # Use full GPT-4o for final synthesis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.5,
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating final summary: {e}")
            return "Error generating comprehensive summary. Please try again later."


# Parse ISO 8601 duration format (PT1H30M15S) to seconds
def parse_duration(duration):
    # Remove 'PT' prefix
    duration = duration[2:]

    hours = 0
    minutes = 0
    seconds = 0

    # Extract hours, minutes, seconds
    hour_match = re.search(r"(\d+)H", duration)
    minute_match = re.search(r"(\d+)M", duration)
    second_match = re.search(r"(\d+)S", duration)

    if hour_match:
        hours = int(hour_match.group(1))
    if minute_match:
        minutes = int(minute_match.group(1))
    if second_match:
        seconds = int(second_match.group(1))

    return hours * 3600 + minutes * 60 + seconds


# Update user usage data
def update_user_usage(user_id, duration_minutes, video_id, title, summary):
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        initialize_new_user(user_id)

    # Add the video to history and update minutes used
    timestamp = datetime.now()
    video_entry = {
        "video_id": video_id,
        "title": title,
        "duration_minutes": round(duration_minutes, 2),
        "processed_at": timestamp,
        "summary": summary,
    }

    # Update the user document atomically
    user_ref.update(
        {
            "usage.minutes_used_this_month": firestore.Increment(
                round(duration_minutes, 2)
            ),
            "usage.video_history": firestore.ArrayUnion([video_entry]),
        }
    )


# Update user subscription
def update_user_subscription(user_id, plan_id, payment_id):
    today = datetime.now()
    # Set billing date to the first day of next month
    next_billing_date = today + relativedelta(
        months=1, day=1, hour=0, minute=0, second=0, microsecond=0
    )

    subscription_data = {
        "plan": plan_id,
        "start_date": today,
        "next_billing_date": next_billing_date,
        "status": "active",
    }

    if payment_id:
        subscription_data["payment_id"] = payment_id

    # Update the user's subscription in Firestore
    user_ref = db.collection("users").document(user_id)
    user_ref.update({"subscription": subscription_data})


if __name__ == "__main__":
    app.run(debug=True)
