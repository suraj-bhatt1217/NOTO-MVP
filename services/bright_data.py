import os
import logging
import json
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
        """
        Get the webhook URL for Bright Data callbacks.
        
        Priority order:
        1. API_BASE_URL environment variable (manually set)
        2. RAILWAY_PUBLIC_DOMAIN (if deployed on Railway)
        3. VERCEL_URL (if deployed on Vercel)
        4. Default fallback (should be replaced in production)
        """
        # Check for manually set API_BASE_URL first
        base_url = os.getenv('API_BASE_URL')
        
        # If not set, try to auto-detect from deployment platform
        if not base_url:
            # Railway provides RAILWAY_PUBLIC_DOMAIN in some cases
            railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
            if railway_domain:
                base_url = f"https://{railway_domain}"
            # Vercel provides VERCEL_URL
            elif os.getenv('VERCEL_URL'):
                base_url = f"https://{os.getenv('VERCEL_URL')}"
            # Default fallback (should be set manually in production)
            else:
                base_url = os.getenv('API_BASE_URL', 'https://your-production-url.com')
                logger.warning(
                    "API_BASE_URL not set. Bright Data webhooks will not work. "
                    "Please set API_BASE_URL to your production URL (e.g., https://your-app.up.railway.app)"
                )
        
        # Ensure URL has protocol
        if not base_url.startswith(('http://', 'https://')):
            base_url = f'https://{base_url}'
        
        webhook_url = f"{base_url}/api/webhooks/brightdata"
        logger.info(f"Webhook URL configured: {webhook_url}")
        return webhook_url

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
        
        # Match Bright Data's recommended parameters
        request_params = {
            "dataset_id": self.dataset_id,
            "format": "json",
            "uncompressed_webhook": "true",
            "include_errors": "true",
        }
        
        # Add webhook endpoint if configured
        if webhook_url and webhook_url != "https://your-production-url.com/api/webhooks/brightdata":
            request_params["endpoint"] = webhook_url
            webhook_auth = os.getenv('WEBHOOK_AUTH_SECRET', '')
            if webhook_auth:
                request_params["auth_header"] = f"Bearer {webhook_auth}"
        
        # Payload format matching Bright Data's example
        request_payload = [
            {
                "url": youtube_url,
                "country": "",
                "transcription_language": ""
            }
        ]
        
        try:
            print("\n" + "="*80)
            print("BRIGHT DATA API REQUEST")
            print("="*80)
            print(f"URL: {self.base_url}")
            print(f"Headers: Authorization: Bearer {self.api_key[:20]}...")
            print(f"Params: {request_params}")
            print(f"Payload: {json.dumps(request_payload, indent=2)}")
            print("="*80 + "\n")
            
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
                
                print("\n" + "="*80)
                print("BRIGHT DATA API RESPONSE")
                print("="*80)
                print(f"Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                
                try:
                    result = response.json()
                    print(f"Response JSON:")
                    print(json.dumps(result, indent=2, default=str))
                    
                    # Save full response to file for analysis
                    try:
                        with open('bright_data_response.json', 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, default=str)
                        print(f"\n💾 Full response saved to: bright_data_response.json")
                    except Exception as save_error:
                        logger.warning(f"Could not save response to file: {save_error}")
                    
                except Exception as json_error:
                    print(f"Response Text (not JSON): {response.text}")
                    result = {"raw_response": response.text}
                    # Save text response
                    try:
                        with open('bright_data_response.txt', 'w', encoding='utf-8') as f:
                            f.write(response.text)
                        print(f"\n💾 Full response saved to: bright_data_response.txt")
                    except Exception as save_error:
                        logger.warning(f"Could not save response to file: {save_error}")
                
                print("="*80 + "\n")
                
                response.raise_for_status()
                
                return {
                    'success': True,
                    'snapshot_id': result.get('snapshot_id'),
                    'message': 'Transcript extraction started',
                    'raw_response': result
                }
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Error triggering Bright Data extraction: {error_msg}")
            print(f"\nERROR: {error_msg}\n")
            return {
                'success': False,
                'error': error_msg,
                'message': 'Failed to start transcript extraction'
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error triggering Bright Data extraction: {error_msg}")
            print(f"\nERROR: {error_msg}\n")
            return {
                'success': False,
                'error': error_msg,
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
        
        # Extract essential fields from Bright Data webhook
        # Field mapping based on actual Bright Data response structure
        
        # Channel name: prefer handle_name (cleaner), fallback to youtuber (remove @)
        channel_name = data.get('handle_name') or data.get('youtuber', '').lstrip('@') or ''
        
        # Transcript: prefer plain transcript, formatted_transcript is array with timestamps
        transcript = data.get('transcript', '')
        if not transcript and data.get('formatted_transcript'):
            # Fallback: join formatted transcript if plain transcript not available
            formatted = data.get('formatted_transcript', [])
            if isinstance(formatted, list):
                transcript = ' '.join([item.get('text', '') for item in formatted if isinstance(item, dict)])
        
        result = {
            'valid': True,
            # ESSENTIAL FIELDS
            'video_id': data.get('video_id'),
            'title': data.get('title'),
            'transcript': transcript,
            
            # IMPORTANT FIELDS
            'video_length': data.get('video_length', 0),  # Duration in seconds
            'thumbnail_url': data.get('preview_image', ''),
            'published_at': data.get('date_posted'),  # ISO format: "2025-05-05T12:54:24.000Z"
            'channel_name': channel_name,
            'channel_avatar': data.get('avatar_img_channel', ''),
            'channel_url': data.get('channel_url', ''),
            
            # USEFUL FIELDS
            'view_count': data.get('views', 0),
            'like_count': data.get('likes', 0),
            'subscriber_count': data.get('subscribers', 0),
            'description': (data.get('description') or '')[:500],  # Truncate to 500 chars
            
            # OPTIONAL FIELDS
            'quality': data.get('quality_label', ''),
            'num_comments': data.get('num_comments', 0),
            'verified': data.get('verified', False),
            
            # Store raw response for debugging
            'raw_response': data
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
