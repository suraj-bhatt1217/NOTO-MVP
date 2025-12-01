import os
import logging
import httpx
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class BrightDataService:
    def __init__(self):
        self.api_key = os.getenv('BRIGHT_DATA_API_KEY')
        self.dataset_id = os.getenv('BRIGHT_DATA_DATASET_ID')
        self.base_url = 'https://api.brightdata.com/datasets/v3/trigger'
        
        if not all([self.api_key, self.dataset_id]):
            logger.warning("Bright Data API key or dataset ID not configured")

    def get_webhook_url(self) -> str:
        """Get the webhook URL for Bright Data callbacks"""
        base_url = os.getenv('API_BASE_URL', 'https://your-production-url.com')
        if not base_url.startswith(('http://', 'https://')):
            base_url = f'https://{base_url}'
        return f"{base_url}/api/webhooks/brightdata"

    async def trigger_transcript_extraction(self, video_id: str) -> Dict[str, Any]:
        """
        Trigger Bright Data to extract transcript for a YouTube video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Dict containing job status and metadata
        """
        if not all([self.api_key, self.dataset_id]):
            return {
                'success': False,
                'error': 'Bright Data not configured',
                'message': 'Bright Data API key or dataset ID not configured'
            }

        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        webhook_url = self.get_webhook_url()
        
        request_params = {
            "dataset_id": self.dataset_id,
            "endpoint": webhook_url,
            "format": "json",
            "uncompressed_webhook": "true",
            "auth_header": f"Bearer {os.getenv('WEBHOOK_AUTH_SECRET', '')}"
        }
        
        request_payload = [{"url": youtube_url}]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    params=request_params,
                    json=request_payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    'success': True,
                    'snapshot_id': result.get('snapshot_id'),
                    'message': 'Transcript extraction started'
                }
                
        except Exception as e:
            logger.error(f"Error triggering Bright Data extraction: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to start transcript extraction'
            }

    @staticmethod
    def parse_webhook_data(payload: Dict) -> Dict[str, Any]:
        """Parse and validate incoming webhook data from Bright Data"""
        if not isinstance(payload, (list, dict)):
            return {'valid': False, 'error': 'Invalid payload format'}
            
        items = payload if isinstance(payload, list) else [payload]
        if not items:
            return {'valid': False, 'error': 'Empty payload'}
            
        # Take the first item (assuming single video per webhook)
        data = items[0]
        
        # Extract essential fields
        result = {
            'valid': True,
            'video_id': data.get('video_id'),
            'title': data.get('title'),
            'video_length': data.get('video_length'),
            'thumbnail_url': data.get('preview_image'),
            'published_at': data.get('date_posted'),
            'channel_name': data.get('youtuber', '').lstrip('@'),
            'channel_avatar': data.get('avatar_img_channel'),
            'channel_url': data.get('channel_url'),
            'view_count': data.get('views', 0),
            'like_count': data.get('likes', 0),
            'subscriber_count': data.get('subscribers', 0),
            'transcript': data.get('transcript') or data.get('formatted_transcript', ''),
            'quality': data.get('quality_label'),
            'description': (data.get('description') or '')[:500],  # Truncate long descriptions
            'raw_response': data  # Store raw response for debugging
        }
        
        # Validate required fields
        if not result['video_id'] or not result['transcript']:
            return {
                'valid': False,
                'error': 'Missing required fields',
                'missing_fields': [
                    field for field in ['video_id', 'transcript'] 
                    if not result.get(field)
                ]
            }
            
        return result
