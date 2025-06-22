"""
Bright Data YouTube Scraper Service
Integrated with the Noto MVP application architecture.
"""
import requests
import json
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse
from config import Config

logger = logging.getLogger(__name__)

@dataclass
class ScrapingJob:
    """Data class for scraping job information."""
    snapshot_id: str
    status: str
    created_at: str
    user_id: str
    video_urls: List[str]

class BrightDataScraper:
    """
    YouTube transcript scraper using Bright Data API.
    Integrated with the Noto MVP application architecture.
    """
    
    def __init__(self, db=None):
        """
        Initialize the scraper with configuration from the app config.
        
        Args:
            db: Firestore database instance
        """
        self.auth_token = Config.BRIGHT_DATA_AUTH_TOKEN
        self.dataset_id = Config.BRIGHT_DATA_DATASET_ID
        self.base_url = "https://api.brightdata.com/datasets/v3"
        self.db = db
        
        if not self.auth_token:
            raise ValueError("BRIGHT_DATA_AUTH_TOKEN not configured")
        
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        logger.info("BrightDataScraper initialized")
    
    def trigger_transcript_collection(self, 
                                    user_id: str,
                                    youtube_urls: List[str],
                                    webhook_url: str,
                                    notify_url: Optional[str] = None) -> ScrapingJob:
        """
        Trigger YouTube transcript collection for the given user.
        
        Args:
            user_id: User ID from the session
            youtube_urls: List of YouTube video URLs
            webhook_url: URL to receive scraped data
            notify_url: Optional URL to receive completion notifications
        
        Returns:
            ScrapingJob object with snapshot_id and status
        
        Raises:
            ValueError: If no valid YouTube URLs provided
            requests.RequestException: If API request fails
        """
        try:
            # Validate YouTube URLs
            validated_urls = self._validate_youtube_urls(youtube_urls)
            if not validated_urls:
                raise ValueError("No valid YouTube URLs provided")
            
            # Prepare request body
            inputs = [{"url": url} for url in validated_urls]
            
            # Prepare query parameters
            params = {
                "dataset_id": self.dataset_id,
                "format": "json",
                "webhook": webhook_url,
                "webhook_format": "json",
                "uncompressed": "false"  # Compress webhook data
            }
            
            if notify_url:
                params["notify"] = notify_url
            
            # Make API request
            response = requests.post(
                f"{self.base_url}/trigger",
                headers=self.headers,
                params=params,
                json=inputs,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            snapshot_id = data.get("snapshot_id")
            if not snapshot_id:
                raise ValueError("No snapshot_id returned from Bright Data API")
            
            # Create scraping job object
            job = ScrapingJob(
                snapshot_id=snapshot_id,
                status=data.get("status", "pending"),
                created_at=data.get("created_at", ""),
                user_id=user_id,
                video_urls=validated_urls
            )
            
            # Store job in database for tracking
            if self.db:
                self._store_job_in_db(job)
            
            logger.info(f"Transcript collection triggered for user {user_id}. Snapshot ID: {snapshot_id}")
            return job
            
        except requests.RequestException as e:
            logger.error(f"Failed to trigger transcript collection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in trigger_transcript_collection: {e}")
            raise
    
    def get_job_status(self, snapshot_id: str) -> Dict:
        """
        Check the status of a scraping job.
        
        Args:
            snapshot_id: Job snapshot ID
            
        Returns:
            Dictionary containing job status information
        """
        try:
            response = requests.get(
                f"{self.base_url}/snapshot/{snapshot_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            status_data = response.json()
            logger.debug(f"Job {snapshot_id} status: {status_data.get('status')}")
            
            return status_data
            
        except requests.RequestException as e:
            logger.error(f"Failed to get job status for {snapshot_id}: {e}")
            raise
    
    def download_results(self, snapshot_id: str) -> Dict:
        """
        Download results when job is complete.
        
        Args:
            snapshot_id: Job snapshot ID
            
        Returns:
            Dictionary containing the scraped data
        """
        try:
            params = {"format": "json"}
            response = requests.get(
                f"{self.base_url}/snapshot/{snapshot_id}",
                headers=self.headers,
                params=params,
                timeout=60
            )
            response.raise_for_status()
            
            results = response.json()
            logger.info(f"Downloaded results for job {snapshot_id}")
            
            return results
            
        except requests.RequestException as e:
            logger.error(f"Failed to download results for {snapshot_id}: {e}")
            raise
    
    def _validate_youtube_urls(self, urls: List[str]) -> List[str]:
        """
        Validate YouTube URLs.
        
        Args:
            urls: List of URLs to validate
            
        Returns:
            List of valid YouTube URLs
        """
        valid_urls = []
        youtube_domains = ["youtube.com", "youtu.be", "m.youtube.com"]
        
        for url in urls:
            try:
                parsed = urlparse(url)
                if any(domain in parsed.netloc for domain in youtube_domains):
                    valid_urls.append(url)
                else:
                    logger.warning(f"Invalid YouTube URL: {url}")
            except Exception as e:
                logger.warning(f"Failed to parse URL {url}: {e}")
        
        return valid_urls
    
    def _store_job_in_db(self, job: ScrapingJob):
        """
        Store scraping job information in the database.
        
        Args:
            job: ScrapingJob object to store
        """
        try:
            if not self.db:
                logger.warning("Database not available, skipping job storage")
                return
            
            job_data = {
                "snapshot_id": job.snapshot_id,
                "status": job.status,
                "created_at": job.created_at,
                "user_id": job.user_id,
                "video_urls": job.video_urls,
                "service": "bright_data",
                "created_timestamp": time.time()
            }
            
            # Store in scraping_jobs collection
            self.db.collection("scraping_jobs").document(job.snapshot_id).set(job_data)
            
            logger.info(f"Stored job {job.snapshot_id} in database")
            
        except Exception as e:
            logger.error(f"Failed to store job in database: {e}")
            # Don't raise here as this is not critical for the scraping process
    
    def get_job_from_db(self, snapshot_id: str) -> Optional[Dict]:
        """
        Retrieve job information from the database.
        
        Args:
            snapshot_id: Job snapshot ID
            
        Returns:
            Job data dictionary or None if not found
        """
        try:
            if not self.db:
                return None
            
            job_doc = self.db.collection("scraping_jobs").document(snapshot_id).get()
            
            if job_doc.exists:
                return job_doc.to_dict()
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve job from database: {e}")
            return None
    
    def update_job_status(self, snapshot_id: str, status: str, additional_data: Optional[Dict] = None):
        """
        Update job status in the database.
        
        Args:
            snapshot_id: Job snapshot ID
            status: New status
            additional_data: Optional additional data to store
        """
        try:
            if not self.db:
                return
            
            update_data = {
                "status": status,
                "updated_at": time.time()
            }
            
            if additional_data:
                update_data.update(additional_data)
            
            self.db.collection("scraping_jobs").document(snapshot_id).update(update_data)
            
            logger.info(f"Updated job {snapshot_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update job status: {e}")

class TranscriptProcessor:
    """
    Process transcript data received from Bright Data webhooks.
    """
    
    def __init__(self, db):
        """
        Initialize the processor.
        
        Args:
            db: Firestore database instance
        """
        self.db = db
        logger.info("TranscriptProcessor initialized")
    
    def process_webhook_data(self, data: List[Dict], snapshot_id: str) -> Dict:
        """
        Process transcript data from webhook.
        
        Args:
            data: List of scraped data items
            snapshot_id: Job snapshot ID
            
        Returns:
            Processing result summary
        """
        try:
            processed_count = 0
            failed_count = 0
            results = []
            
            for item in data:
                try:
                    result = self._process_single_transcript(item, snapshot_id)
                    if result:
                        results.append(result)
                        processed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Failed to process transcript item: {e}")
                    failed_count += 1
            
            summary = {
                "processed_count": processed_count,
                "failed_count": failed_count,
                "total_count": len(data),
                "results": results
            }
            
            logger.info(f"Processed {processed_count}/{len(data)} transcripts for job {snapshot_id}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error processing webhook data: {e}")
            raise
    
    def _process_single_transcript(self, item: Dict, snapshot_id: str) -> Optional[Dict]:
        """
        Process a single transcript item.
        
        Args:
            item: Single scraped data item
            snapshot_id: Job snapshot ID
            
        Returns:
            Processing result or None if failed
        """
        try:
            # Extract required fields
            transcript = item.get("transcript", "")
            video_url = item.get("url", "")
            title = item.get("title", "Unknown Title")
            duration = item.get("duration", "")
            
            if not transcript or not video_url:
                logger.warning(f"Missing transcript or URL in item: {item}")
                return None
            
            # Extract video ID from URL
            from utils import extract_video_id
            video_id = extract_video_id(video_url)
            
            if not video_id:
                logger.warning(f"Could not extract video ID from URL: {video_url}")
                return None
            
            # Store transcript data
            transcript_data = {
                "video_id": video_id,
                "video_url": video_url,
                "title": title,
                "transcript": transcript,
                "duration": duration,
                "snapshot_id": snapshot_id,
                "processed_at": time.time(),
                "source": "bright_data"
            }
            
            # Store in transcripts collection
            self.db.collection("transcripts").document(video_id).set(transcript_data)
            
            logger.info(f"Processed transcript for video: {title} ({video_id})")
            
            return {
                "video_id": video_id,
                "title": title,
                "transcript_length": len(transcript)
            }
            
        except Exception as e:
            logger.error(f"Error processing single transcript: {e}")
            return None
