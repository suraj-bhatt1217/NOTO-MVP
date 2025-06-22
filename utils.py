"""
Utility functions for the Noto MVP application.
"""
import re
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import openai
from config import Config

logger = logging.getLogger(__name__)

def initialize_new_user(db, user_id):
    """Initialize a new user with default settings."""
    try:
        user_ref = db.collection("users").document(user_id)
        user_data = {
            "subscription": {
                "plan": "free",
                "payment_id": None,
                "start_date": datetime.now(),
                "next_billing_date": datetime.now() + relativedelta(months=1),
            },
            "usage": {
                "minutes_used_this_month": 0,
                "videos_processed": 0,
                "last_reset_date": datetime.now(),
            },
            "created_at": datetime.now(),
        }
        user_ref.set(user_data)
        logger.info(f"Initialized new user: {user_id}")
    except Exception as e:
        logger.error(f"Error initializing user {user_id}: {str(e)}")
        raise

def extract_video_id(url):
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_transcript(video_id):
    """Get video transcript from YouTube."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript_list])
    except (NoTranscriptFound, TranscriptsDisabled) as e:
        logger.warning(f"No transcript found for video {video_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error getting transcript for video {video_id}: {str(e)}")
        raise

def generate_summary(transcript, plan_type, title, channel):
    """Generate summary from transcript using OpenAI."""
    try:
        # Set OpenAI API key
        openai.api_key = Config.OPENAI_API_KEY
        
        # Customize prompt based on plan type
        if plan_type == "free":
            prompt = f"""
            Summarize this YouTube video transcript in a concise manner:
            
            Title: {title}
            Channel: {channel}
            
            Transcript: {transcript[:3000]}...
            
            Provide a brief summary highlighting the main points.
            """
            max_tokens = 200
        else:  # pro or elite
            prompt = f"""
            Provide a comprehensive summary of this YouTube video transcript:
            
            Title: {title}
            Channel: {channel}
            
            Transcript: {transcript}
            
            Please include:
            1. Main topic and key points
            2. Important details and examples
            3. Actionable insights or takeaways
            4. Any relevant timestamps or sections
            
            Format the response in a clear, structured manner.
            """
            max_tokens = 800 if plan_type == "pro" else 1200

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates video summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"Generated summary for video with {len(transcript)} characters")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise

def parse_duration(duration):
    """Parse ISO 8601 duration format (PT1H30M15S) to seconds."""
    if not duration:
        return 0
        
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if not match:
        return 0
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds

def update_user_usage(db, user_id, duration_minutes, video_id, title, summary):
    """Update user usage data."""
    try:
        user_ref = db.collection("users").document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            initialize_new_user(db, user_id)
            user_doc = user_ref.get()
        
        user_data = user_doc.to_dict()
        current_usage = user_data.get("usage", {})
        
        # Update usage
        new_usage = {
            "minutes_used_this_month": current_usage.get("minutes_used_this_month", 0) + duration_minutes,
            "videos_processed": current_usage.get("videos_processed", 0) + 1,
            "last_reset_date": current_usage.get("last_reset_date", datetime.now()),
        }
        
        # Store video summary
        video_data = {
            "video_id": video_id,
            "title": title,
            "summary": summary,
            "duration_minutes": duration_minutes,
            "processed_at": datetime.now(),
        }
        
        # Update user document
        user_ref.update({"usage": new_usage})
        
        # Store video in user's videos collection
        user_ref.collection("videos").document(video_id).set(video_data)
        
        logger.info(f"Updated usage for user {user_id}: +{duration_minutes} minutes")
        
    except Exception as e:
        logger.error(f"Error updating user usage for {user_id}: {str(e)}")
        raise

def update_user_subscription(db, user_id, plan_id, payment_id):
    """Update user subscription."""
    try:
        user_ref = db.collection("users").document(user_id)
        
        subscription_data = {
            "plan": plan_id,
            "payment_id": payment_id,
            "start_date": datetime.now(),
            "next_billing_date": datetime.now() + relativedelta(months=1),
            "updated_at": datetime.now(),
        }
        
        user_ref.update({"subscription": subscription_data})
        logger.info(f"Updated subscription for user {user_id} to {plan_id}")
        
    except Exception as e:
        logger.error(f"Error updating subscription for user {user_id}: {str(e)}")
        raise

def validate_youtube_url(url):
    """Validate if URL is a valid YouTube URL."""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
    return False
