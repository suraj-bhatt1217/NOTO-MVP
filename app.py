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
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
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
        "currency": "INR",
        "features": ["Basic Summaries", "Limited to 30 min/month"],
    },
    "pro": {
        "name": "Pro Plan",
        "minutes_limit": 300,  # 300 minutes per month
        "price": 29900,  # ₹299 in paise
        "currency": "INR",
        "features": ["Premium Summaries", "300 min/month", "Unlimited Videos"],
    },
    "elite": {
        "name": "Elite Plan",
        "minutes_limit": 1000,  # 1000 minutes per month
        "price": 79900,  # ₹799 in paise
        "currency": "INR",
        "features": [
            "Premium Summaries",
            "1000 min/month",
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
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


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


@app.route("/api/summarize-video", methods=["POST"])
@auth_required
@plan_checker
def summarize_video():
    data = request.json
    video_url = data.get("video_url", "")

    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "Invalid YouTube URL"}), 400

        # Extract transcript
        transcript = get_video_transcript(video_id)
        if not transcript:
            return (
                jsonify({"error": "Could not extract transcript from this video"}),
                400,
            )

        # Get video info for duration tracking
        api_key = os.getenv("YOUTUBE_API_KEY")
        video_details_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=snippet,contentDetails"
        response = requests.get(video_details_url)
        video_data = response.json()

        if not video_data.get("items"):
            return jsonify({"error": "Video not found or unavailable"}), 404

        video_info = video_data["items"][0]
        duration_seconds = parse_duration(video_info["contentDetails"]["duration"])
        duration_minutes = duration_seconds / 60
        title = video_info["snippet"]["title"]
        channel = video_info["snippet"]["channelTitle"]

        # Check if the video duration would exceed the user's remaining minutes
        user_id = session["user"]["uid"]
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get().to_dict()
        plan_type = user_doc.get("subscription", {}).get("plan", "free")
        
        # Get current usage and plan limit
        usage_minutes = user_doc.get("usage", {}).get("minutes_used_this_month", 0)
        plan_limit = SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]
        remaining_minutes = plan_limit - usage_minutes
        
        # Check if this video would exceed the remaining minutes
        if duration_minutes > remaining_minutes:
            return (
                jsonify(
                    {
                        "error": "Plan limit would be exceeded",
                        "minutes_used": usage_minutes,
                        "video_duration": round(duration_minutes, 2),
                        "remaining_minutes": round(remaining_minutes, 2),
                        "plan_limit": plan_limit,
                        "message": f"This video is {round(duration_minutes, 2)} minutes long, but you only have {round(remaining_minutes, 2)} minutes remaining in your plan. Please upgrade your plan to process longer videos.",
                    }
                ),
                403,
            )

        summary = generate_summary(transcript, plan_type, title, channel)

        # Update user's usage
        update_user_usage(user_id, duration_minutes, video_id, title, summary)

        return jsonify(
            {
                "video_id": video_id,
                "title": title,
                "duration_minutes": round(duration_minutes, 2),
                "summary": summary,
                "transcript": (
                    transcript[:1000] + "..." if len(transcript) > 1000 else transcript
                ),  # Shortened transcript preview
            }
        )

    except NoTranscriptFound:
        return jsonify({"error": "No transcript found for this video"}), 404

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts are disabled for this video"}), 403

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
        # Create an order
        order_amount = plan_data["price"]  # amount in paise
        order_currency = plan_data["currency"]
        order_receipt = f"order_rcptid_{secrets.token_hex(6)}"
        notes = {"user_id": user_id, "plan_id": plan_id}

        order = razorpay_client.order.create(
            {
                "amount": order_amount,
                "currency": order_currency,
                "receipt": order_receipt,
                "notes": notes,
            }
        )

        return jsonify(
            {
                "order_id": order["id"],
                "amount": order_amount,
                "currency": order_currency,
                "key_id": RAZORPAY_KEY_ID,
                "product_name": plan_data["name"],
                "description": f"Subscription to {plan_data['name']}",
                "user_info": {
                    "name": session["user"].get("name", "Customer"),
                    "email": user_email,
                    "contact": session["user"].get("phoneNumber", ""),
                },
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
def get_video_transcript(video_id):
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    transcript_text = " ".join([t.get("text", "") for t in transcript_list])
    return transcript_text


# Generate summary from transcript
def generate_summary(transcript, plan_type, title, channel):
    # Different summary types based on subscription plan
    if plan_type == "free":
        system_prompt = """You are an AI assistant that creates basic summaries of YouTube video transcripts. 
        Create a simple summary that covers the main points in a concise way."""
        max_tokens = 500
    else:  # 'pro' or 'elite'
        system_prompt = """You are an AI assistant that creates premium structured summaries of YouTube video transcripts.
        Format your response with these sections:
        1. SUMMARY: A concise overview of the video content
        2. KEY POINTS: Bullet points of the most important information
        3. INSIGHTS: Notable observations or takeaways
        4. ACTIONABLE TIPS: Practical advice from the video
        Use markdown formatting for better readability."""
        max_tokens = 1000 if plan_type == "pro" else 1500

    prompt = f"Video Title: {title}\nChannel: {channel}\n\nTranscript: {transcript[:15000]}"  # Limit transcript size

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini as it's more affordable while offering good quality
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
