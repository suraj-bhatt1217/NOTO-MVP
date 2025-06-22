"""
Webhook routes blueprint for handling Bright Data callbacks.
"""
import logging
import json
from flask import Blueprint, request, jsonify
from services.bright_data_scraper import BrightDataScraper, TranscriptProcessor
from utils import generate_summary, update_user_usage, parse_duration
from config import Config

logger = logging.getLogger(__name__)

def create_webhook_blueprint(db):
    """Factory function to create webhook blueprint with database dependency."""
    webhook_bp = Blueprint('webhook', __name__)
    
    scraper = BrightDataScraper(db)
    processor = TranscriptProcessor(db)

    @webhook_bp.route("/webhook/bright-data", methods=["POST"])
    def handle_bright_data_webhook():
        """
        Handle webhook data delivery from Bright Data.
        This endpoint receives the scraped transcript data.
        """
        try:
            # Get the data from the webhook
            content_type = request.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = request.get_json()
            else:
                # Handle compressed or other formats
                data = json.loads(request.get_data(as_text=True))
            
            if not data:
                logger.warning("Empty webhook data received")
                return jsonify({"error": "No data received"}), 400
            
            # Extract snapshot_id from headers or data
            snapshot_id = request.headers.get('X-Snapshot-Id') or data[0].get('snapshot_id') if data else None
            
            if not snapshot_id:
                logger.error("No snapshot_id found in webhook data")
                return jsonify({"error": "Missing snapshot_id"}), 400
            
            logger.info(f"Received webhook data for job {snapshot_id}: {len(data)} records")
            
            # Get job information from database
            job_data = scraper.get_job_from_db(snapshot_id)
            if not job_data:
                logger.warning(f"Job {snapshot_id} not found in database")
                return jsonify({"error": "Job not found"}), 404
            
            user_id = job_data.get('user_id')
            if not user_id:
                logger.error(f"No user_id found for job {snapshot_id}")
                return jsonify({"error": "Invalid job data"}), 400
            
            # Process the transcript data
            processing_result = processor.process_webhook_data(data, snapshot_id)
            
            # Generate summaries for each processed transcript
            summary_results = []
            for item in data:
                try:
                    result = _generate_summary_for_transcript(db, item, user_id, snapshot_id)
                    if result:
                        summary_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to generate summary for transcript: {e}")
            
            # Update job status
            scraper.update_job_status(snapshot_id, "completed", {
                "processing_result": processing_result,
                "summary_results": summary_results,
                "completed_at": json.dumps({"timestamp": "now"}, default=str)
            })
            
            logger.info(f"Successfully processed webhook for job {snapshot_id}")
            
            return jsonify({
                "status": "success",
                "processed_count": processing_result["processed_count"],
                "summaries_generated": len(summary_results)
            }), 200
            
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            return jsonify({"error": "Internal processing error"}), 500

    @webhook_bp.route("/webhook/bright-data/notify", methods=["POST"])
    def handle_bright_data_notification():
        """
        Handle completion notifications from Bright Data.
        This endpoint receives job status updates.
        """
        try:
            data = request.get_json()
            
            if not data:
                logger.warning("Empty notification data received")
                return jsonify({"error": "No data received"}), 400
            
            snapshot_id = data.get("snapshot_id")
            status = data.get("status")
            
            if not snapshot_id:
                logger.error("No snapshot_id in notification")
                return jsonify({"error": "Missing snapshot_id"}), 400
            
            logger.info(f"Received notification for job {snapshot_id}: status={status}")
            
            # Update job status in database
            scraper.update_job_status(snapshot_id, status, {
                "notification_received_at": json.dumps({"timestamp": "now"}, default=str),
                "notification_data": data
            })
            
            # Handle different status types
            if status == "ready":
                logger.info(f"Job {snapshot_id} completed successfully")
                # If using notifications instead of webhooks, could download results here
                # results = scraper.download_results(snapshot_id)
                # processor.process_webhook_data(results, snapshot_id)
            elif status in ["failed", "error"]:
                logger.error(f"Job {snapshot_id} failed: {data}")
                # Could notify user of failure here
            
            return jsonify({"status": "received"}), 200
            
        except Exception as e:
            logger.error(f"Notification processing error: {e}")
            return jsonify({"error": "Internal processing error"}), 500

    def _generate_summary_for_transcript(db, transcript_item, user_id, snapshot_id):
        """
        Generate summary for a single transcript and update user usage.
        
        Args:
            db: Database instance
            transcript_item: Single transcript data item
            user_id: User ID
            snapshot_id: Job snapshot ID
            
        Returns:
            Summary result or None if failed
        """
        try:
            # Extract transcript data
            transcript = transcript_item.get("transcript", "")
            title = transcript_item.get("title", "Unknown Title")
            video_url = transcript_item.get("url", "")
            duration_str = transcript_item.get("duration", "")
            
            if not transcript:
                logger.warning("No transcript found in item")
                return None
            
            # Extract video ID
            from utils import extract_video_id
            video_id = extract_video_id(video_url)
            
            if not video_id:
                logger.warning(f"Could not extract video ID from {video_url}")
                return None
            
            # Parse duration
            duration_minutes = 1  # Default minimum
            if duration_str:
                try:
                    duration_seconds = parse_duration(duration_str)
                    duration_minutes = max(1, round(duration_seconds / 60))
                except:
                    logger.warning(f"Could not parse duration: {duration_str}")
            
            # Get user's plan type
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                plan_type = user_data.get("subscription", {}).get("plan", "free")
            else:
                plan_type = "free"
            
            # Generate summary
            channel = transcript_item.get("channel", "Unknown Channel")
            summary = generate_summary(transcript, plan_type, title, channel)
            
            # Update user usage
            update_user_usage(db, user_id, duration_minutes, video_id, title, summary)
            
            logger.info(f"Generated summary for {title} (user: {user_id})")
            
            return {
                "video_id": video_id,
                "title": title,
                "summary": summary,
                "duration_minutes": duration_minutes,
                "snapshot_id": snapshot_id
            }
            
        except Exception as e:
            logger.error(f"Error generating summary for transcript: {e}")
            return None

    return webhook_bp
