"""
Main routes blueprint for the Noto MVP application.
"""
import logging
from flask import Blueprint, render_template, request, session, jsonify
from auth import auth_required, plan_checker, get_current_user_id
from utils import validate_youtube_url, extract_video_id, get_video_transcript, generate_summary, parse_duration, update_user_usage
import requests
from config import Config

logger = logging.getLogger(__name__)

def create_main_blueprint(db):
    """Factory function to create main blueprint with database dependency."""
    main_bp = Blueprint('main', __name__)
    
    # Apply plan_checker decorator with database
    plan_check = plan_checker(db)

    @main_bp.route("/")
    def home():
        """Render home page."""
        return render_template("home.html")

    @main_bp.route("/terms")
    def terms():
        """Render terms of service page."""
        return render_template("terms.html")

    @main_bp.route("/privacy")
    def privacy():
        """Render privacy policy page."""
        return render_template("privacy.html")

    @main_bp.route("/dashboard")
    @auth_required
    def dashboard():
        """Render user dashboard."""
        try:
            user_id = get_current_user_id()
            
            # Get user data
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                plan_type = user_data.get("subscription", {}).get("plan", "free")
                usage_minutes = user_data.get("usage", {}).get("minutes_used_this_month", 0)
                plan_limit = Config.SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]
                
                return render_template("dashboard.html", 
                                     plan_type=plan_type,
                                     usage_minutes=usage_minutes,
                                     plan_limit=plan_limit)
            else:
                # Initialize new user
                from utils import initialize_new_user
                initialize_new_user(db, user_id)
                return render_template("dashboard.html", 
                                     plan_type="free",
                                     usage_minutes=0,
                                     plan_limit=30)
                
        except Exception as e:
            logger.error(f"Error loading dashboard for user {user_id}: {str(e)}")
            return render_template("dashboard.html", 
                                 plan_type="free",
                                 usage_minutes=0,
                                 plan_limit=30)

    @main_bp.route("/pricing")
    @auth_required
    def pricing():
        """Render pricing page."""
        return render_template("pricing.html", plans=Config.SUBSCRIPTION_PLANS)

    @main_bp.route("/my-videos")
    @auth_required
    def my_videos():
        """Render user's video history."""
        try:
            user_id = get_current_user_id()
            
            # Get user's videos
            videos_ref = db.collection("users").document(user_id).collection("videos")
            videos = videos_ref.order_by("processed_at", direction="DESCENDING").limit(20).stream()
            
            video_list = []
            for video in videos:
                video_data = video.to_dict()
                video_list.append({
                    "video_id": video_data.get("video_id"),
                    "title": video_data.get("title"),
                    "duration_minutes": video_data.get("duration_minutes"),
                    "processed_at": video_data.get("processed_at")
                })
            
            return render_template("my_videos.html", videos=video_list)
            
        except Exception as e:
            logger.error(f"Error loading videos for user {user_id}: {str(e)}")
            return render_template("my_videos.html", videos=[])

    @main_bp.route("/api/extract-video-info", methods=["POST"])
    @auth_required
    def extract_video_info():
        """Extract video information from YouTube URL."""
        try:
            data = request.json
            url = data.get("url", "").strip()
            
            if not url:
                return jsonify({"error": "URL is required"}), 400
            
            if not validate_youtube_url(url):
                return jsonify({"error": "Invalid YouTube URL"}), 400
            
            video_id = extract_video_id(url)
            if not video_id:
                return jsonify({"error": "Could not extract video ID from URL"}), 400
            
            # Get video details from YouTube API
            api_key = Config.YOUTUBE_API_KEY
            if not api_key:
                return jsonify({"error": "YouTube API not configured"}), 500
            
            youtube_url = f"https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet,contentDetails",
                "id": video_id,
                "key": api_key
            }
            
            response = requests.get(youtube_url, params=params)
            
            if response.status_code != 200:
                logger.error(f"YouTube API error: {response.status_code}")
                return jsonify({"error": "Failed to fetch video details"}), 500
            
            data = response.json()
            
            if not data.get("items"):
                return jsonify({"error": "Video not found"}), 404
            
            video_info = data["items"][0]
            snippet = video_info["snippet"]
            content_details = video_info["contentDetails"]
            
            duration_seconds = parse_duration(content_details.get("duration", ""))
            duration_minutes = max(1, round(duration_seconds / 60))  # Minimum 1 minute
            
            return jsonify({
                "video_id": video_id,
                "title": snippet.get("title", "Unknown Title"),
                "channel": snippet.get("channelTitle", "Unknown Channel"),
                "duration_minutes": duration_minutes,
                "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", "")
            })
            
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return jsonify({"error": "Failed to extract video information"}), 500

    @main_bp.route("/api/summarize-video", methods=["POST"])
    @auth_required
    @plan_check
    def summarize_video():
        """Trigger asynchronous YouTube video summarization using Bright Data."""
        try:
            data = request.json
            video_id = data.get("video_id")
            title = data.get("title", "Unknown Title")
            channel = data.get("channel", "Unknown Channel")
            duration_minutes = data.get("duration_minutes", 1)
            video_url = data.get("video_url")
            
            if not video_id or not video_url:
                return jsonify({"error": "Video ID and URL are required"}), 400
            
            user_id = get_current_user_id()
            
            # Check if we already have this transcript
            transcript_doc = db.collection("transcripts").document(video_id).get()
            if transcript_doc.exists:
                # Use existing transcript
                transcript_data = transcript_doc.to_dict()
                transcript = transcript_data.get("transcript", "")
                
                if transcript:
                    # Generate summary directly
                    user_ref = db.collection("users").document(user_id)
                    user_doc = user_ref.get()
                    user_data = user_doc.to_dict()
                    plan_type = user_data.get("subscription", {}).get("plan", "free")
                    
                    try:
                        summary = generate_summary(transcript, plan_type, title, channel)
                        update_user_usage(db, user_id, duration_minutes, video_id, title, summary)
                        
                        return jsonify({
                            "success": True,
                            "summary": summary,
                            "video_id": video_id,
                            "title": title,
                            "channel": channel,
                            "duration_minutes": duration_minutes,
                            "processing_type": "cached"
                        })
                    except Exception as e:
                        logger.error(f"Error generating summary from cached transcript: {str(e)}")
                        return jsonify({"error": "Failed to generate summary"}), 500
            
            # Trigger Bright Data scraping for new transcript
            try:
                from services.bright_data_scraper import BrightDataScraper
                from flask import url_for
                
                scraper = BrightDataScraper(db)
                
                # Construct webhook URL
                webhook_url = url_for('webhook.handle_bright_data_webhook', _external=True)
                notify_url = url_for('webhook.handle_bright_data_notification', _external=True)
                
                # Trigger scraping job
                job = scraper.trigger_transcript_collection(
                    user_id=user_id,
                    youtube_urls=[video_url],
                    webhook_url=webhook_url,
                    notify_url=notify_url
                )
                
                # Store job reference for this video
                job_ref_data = {
                    "snapshot_id": job.snapshot_id,
                    "user_id": user_id,
                    "video_id": video_id,
                    "title": title,
                    "channel": channel,
                    "duration_minutes": duration_minutes,
                    "status": "processing",
                    "created_at": job.created_at
                }
                
                db.collection("video_jobs").document(video_id).set(job_ref_data)
                
                return jsonify({
                    "success": True,
                    "processing": True,
                    "job_id": job.snapshot_id,
                    "video_id": video_id,
                    "title": title,
                    "channel": channel,
                    "duration_minutes": duration_minutes,
                    "message": "Video is being processed. You'll receive the summary shortly.",
                    "processing_type": "async"
                })
                
            except Exception as e:
                logger.error(f"Error triggering Bright Data scraping: {str(e)}")
                
                # Fallback to direct transcript API if Bright Data fails
                try:
                    transcript = get_video_transcript(video_id)
                    
                    user_ref = db.collection("users").document(user_id)
                    user_doc = user_ref.get()
                    user_data = user_doc.to_dict()
                    plan_type = user_data.get("subscription", {}).get("plan", "free")
                    
                    summary = generate_summary(transcript, plan_type, title, channel)
                    update_user_usage(db, user_id, duration_minutes, video_id, title, summary)
                    
                    return jsonify({
                        "success": True,
                        "summary": summary,
                        "video_id": video_id,
                        "title": title,
                        "channel": channel,
                        "duration_minutes": duration_minutes,
                        "processing_type": "fallback"
                    })
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback transcript fetch also failed: {str(fallback_error)}")
                    return jsonify({"error": "This video doesn't have a transcript available"}), 400
            
        except Exception as e:
            logger.error(f"Error in summarize_video: {str(e)}")
            return jsonify({"error": "Failed to process video"}), 500

    @main_bp.route("/api/get-user-usage")
    @auth_required
    def get_user_usage():
        """Get current user's usage statistics."""
        try:
            user_id = get_current_user_id()
            
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                from utils import initialize_new_user
                initialize_new_user(db, user_id)
                user_doc = user_ref.get()
            
            user_data = user_doc.to_dict()
            usage = user_data.get("usage", {})
            subscription = user_data.get("subscription", {})
            
            plan_type = subscription.get("plan", "free")
            plan_limit = Config.SUBSCRIPTION_PLANS[plan_type]["minutes_limit"]
            
            return jsonify({
                "minutes_used": usage.get("minutes_used_this_month", 0),
                "plan_limit": plan_limit,
                "plan_type": plan_type,
                "videos_processed": usage.get("videos_processed", 0)
            })
            
        except Exception as e:
            logger.error(f"Error getting user usage: {str(e)}")
            return jsonify({"error": "Failed to get usage data"}), 500

    @main_bp.route("/api/get-recent-videos")
    @auth_required
    def get_recent_videos():
        """Get user's recent videos."""
        try:
            user_id = get_current_user_id()
            
            videos_ref = db.collection("users").document(user_id).collection("videos")
            videos = videos_ref.order_by("processed_at", direction="DESCENDING").limit(5).stream()
            
            video_list = []
            for video in videos:
                video_data = video.to_dict()
                video_list.append({
                    "video_id": video_data.get("video_id"),
                    "title": video_data.get("title"),
                    "duration_minutes": video_data.get("duration_minutes"),
                    "processed_at": video_data.get("processed_at").isoformat() if video_data.get("processed_at") else None
                })
            
            return jsonify({"videos": video_list})
            
        except Exception as e:
            logger.error(f"Error getting recent videos: {str(e)}")
            return jsonify({"error": "Failed to get recent videos"}), 500

    @main_bp.route("/api/get-video-details/<video_id>")
    @auth_required
    def get_video_details(video_id):
        """Get details for a specific video."""
        try:
            user_id = get_current_user_id()
            
            video_ref = db.collection("users").document(user_id).collection("videos").document(video_id)
            video_doc = video_ref.get()
            
            if not video_doc.exists:
                return jsonify({"error": "Video not found"}), 404
            
            video_data = video_doc.to_dict()
            
            return jsonify({
                "video_id": video_data.get("video_id"),
                "title": video_data.get("title"),
                "summary": video_data.get("summary"),
                "duration_minutes": video_data.get("duration_minutes"),
                "processed_at": video_data.get("processed_at").isoformat() if video_data.get("processed_at") else None
            })
            
        except Exception as e:
            logger.error(f"Error getting video details: {str(e)}")
            return jsonify({"error": "Failed to get video details"}), 500

    @main_bp.route("/api/check-job-status/<video_id>")
    @auth_required
    def check_job_status(video_id):
        """Check the processing status of a video job."""
        try:
            user_id = get_current_user_id()
            
            # Check if video is already processed
            video_ref = db.collection("users").document(user_id).collection("videos").document(video_id)
            video_doc = video_ref.get()
            
            if video_doc.exists:
                video_data = video_doc.to_dict()
                return jsonify({
                    "status": "completed",
                    "video_id": video_id,
                    "title": video_data.get("title"),
                    "summary": video_data.get("summary"),
                    "duration_minutes": video_data.get("duration_minutes"),
                    "processed_at": video_data.get("processed_at").isoformat() if video_data.get("processed_at") else None
                })
            
            # Check job status
            job_ref = db.collection("video_jobs").document(video_id)
            job_doc = job_ref.get()
            
            if not job_doc.exists:
                return jsonify({"error": "Job not found"}), 404
            
            job_data = job_doc.to_dict()
            
            # Verify user owns this job
            if job_data.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized"}), 403
            
            return jsonify({
                "status": job_data.get("status", "unknown"),
                "video_id": video_id,
                "title": job_data.get("title"),
                "channel": job_data.get("channel"),
                "duration_minutes": job_data.get("duration_minutes"),
                "job_id": job_data.get("snapshot_id"),
                "created_at": job_data.get("created_at")
            })
            
        except Exception as e:
            logger.error(f"Error checking job status: {str(e)}")
            return jsonify({"error": "Failed to check job status"}), 500

    return main_bp
