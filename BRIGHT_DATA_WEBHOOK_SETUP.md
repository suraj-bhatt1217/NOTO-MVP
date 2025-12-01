# Bright Data Webhook Setup Guide for YouTube Transcript Processing

This guide explains how to set up and use Bright Data webhooks for processing YouTube transcripts in the Noto MVP application.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Bright Data Account Setup](#bright-data-account-setup)
4. [Web Scraper API Configuration](#web-scraper-api-configuration)
5. [Environment Variables](#environment-variables)
6. [Webhook Endpoint Configuration](#webhook-endpoint-configuration)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

## Overview

Bright Data provides two API types for YouTube transcript extraction:

1. **Web Scraper API** (Recommended) - Uses collector IDs
2. **Datasets API** (Legacy) - Uses dataset IDs

The application supports both API types. The Web Scraper API is recommended for better performance and more features.

## Prerequisites

- Bright Data account with API access
- YouTube scraper/collector configured in Bright Data dashboard
- Public webhook endpoint URL (HTTPS required)
- Environment variables configured (see below)

## Bright Data Account Setup

### Step 1: Create a Bright Data Account

1. Sign up at [brightdata.com](https://brightdata.com)
2. Complete account verification
3. Navigate to your dashboard

### Step 2: Set Up YouTube Scraper

1. Go to **Web Scraper API** section in your Bright Data dashboard
2. Click **Create Scraper** or select an existing YouTube scraper
3. Choose the **YouTube** template
4. Configure the scraper to extract:
   - Video metadata (title, description, channel info)
   - **Transcript** (required)
   - **Formatted transcript** (optional but recommended)
   - Engagement metrics (views, likes, etc.)

### Step 3: Get Your Credentials

From your Bright Data dashboard, collect:

- **API Key** (also called Auth Token)
  - Location: Account Settings → API → Generate API Key
  - Format: `Bearer <token>` or just the token

- **Collector ID** (for Web Scraper API)
  - Location: Scraper settings → Overview
  - Format: `hl_81577a46` or similar
  - Found in the scraper URL: `.../scrapers/api/gd_.../pdp/overview?id=hl_...`

- **Dataset ID** (for Datasets API - legacy)
  - Location: Datasets section → Your dataset
  - Only needed if using Datasets API

## Web Scraper API Configuration

### Using Web Scraper API (Recommended)

The Web Scraper API uses collector IDs and provides better performance.

**Endpoint Format:**
```
https://api.brightdata.com/scrapers/v1/collector/{collector_id}/trigger
```

**Configuration:**
1. Set `BRIGHT_DATA_API_TYPE=scraper` in your environment
2. Set `BRIGHT_DATA_COLLECTOR_ID` to your collector ID (e.g., `hl_81577a46`)
3. Set `BRIGHT_DATA_API_KEY` to your API key

### Using Datasets API (Legacy)

If you're using the older Datasets API:

**Endpoint Format:**
```
https://api.brightdata.com/datasets/v3/trigger
```

**Configuration:**
1. Set `BRIGHT_DATA_API_TYPE=dataset` in your environment
2. Set `BRIGHT_DATA_DATASET_ID` to your dataset ID
3. Set `BRIGHT_DATA_API_KEY` to your API key

## Environment Variables

Add the following environment variables to your `.env` file or deployment platform:

### Required Variables

```bash
# Bright Data API Configuration
BRIGHT_DATA_API_KEY=your_bright_data_api_key_here
BRIGHT_DATA_API_TYPE=scraper  # or 'dataset' for legacy API

# For Web Scraper API (if API_TYPE=scraper)
BRIGHT_DATA_COLLECTOR_ID=hl_81577a46

# For Datasets API (if API_TYPE=dataset)
BRIGHT_DATA_DATASET_ID=your_dataset_id_here

# Webhook Configuration
API_BASE_URL=https://your-production-domain.com
WEBHOOK_AUTH_SECRET=your_secure_webhook_secret_here
```

### Variable Descriptions

- **BRIGHT_DATA_API_KEY**: Your Bright Data API authentication token
- **BRIGHT_DATA_API_TYPE**: Either `scraper` (recommended) or `dataset` (legacy)
- **BRIGHT_DATA_COLLECTOR_ID**: Your collector ID from Web Scraper API (required if API_TYPE=scraper)
- **BRIGHT_DATA_DATASET_ID**: Your dataset ID (required if API_TYPE=dataset)
- **API_BASE_URL**: Your production domain (must be HTTPS for webhooks)
- **WEBHOOK_AUTH_SECRET**: A secure secret for webhook authentication (generate a random string)

### Generating WEBHOOK_AUTH_SECRET

Generate a secure random secret:

```python
import secrets
print(secrets.token_hex(32))
```

Or use:
```bash
openssl rand -hex 32
```

## Webhook Endpoint Configuration

### Step 1: Configure Webhook in Bright Data Dashboard

1. Navigate to your scraper/collector settings
2. Go to **Data Delivery** or **Webhooks** section
3. Add your webhook URL:
   ```
   https://your-production-domain.com/api/webhooks/brightdata
   ```
4. Configure webhook settings:
   - **Format**: JSON
   - **Authentication**: Bearer Token
   - **Auth Header**: `Bearer {WEBHOOK_AUTH_SECRET}`
   - **Uncompressed**: Enable (if available)

### Step 2: Verify Webhook Endpoint

The webhook endpoint is already implemented at:
```
POST /api/webhooks/brightdata
```

**Expected Headers:**
- `Authorization: Bearer {WEBHOOK_AUTH_SECRET}`
- `Content-Type: application/json`

**Expected Payload Format:**
```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "transcript": "Full transcript text...",
  "formatted_transcript": "Formatted transcript...",
  "video_length": 240,
  "preview_image": "https://...",
  "date_posted": "2024-01-01",
  "youtuber": "@channel",
  "views": 1000000,
  "likes": 50000,
  ...
}
```

## Testing

### Test 1: Verify Configuration

Check that your environment variables are set correctly:

```python
from services.bright_data import BrightDataService

service = BrightDataService()
print(f"API Type: {service.api_type}")
print(f"Base URL: {service.base_url}")
print(f"Webhook URL: {service.get_webhook_url()}")
```

### Test 2: Trigger a Test Extraction

Use the `/summarize` endpoint to trigger a transcript extraction:

```bash
curl -X POST https://your-domain.com/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_USER_TOKEN" \
  -d '{"video_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### Test 3: Test Webhook Locally

Use a tool like [ngrok](https://ngrok.com) to expose your local server:

```bash
ngrok http 5000
```

Then update `API_BASE_URL` temporarily to the ngrok URL for testing.

### Test 4: Monitor Webhook Logs

Check your application logs for webhook activity:

```bash
# Look for these log messages:
# "--- BRIGHT DATA WEBHOOK RECEIVED ---"
# "Processing webhook for video: {video_id}"
# "Successfully processed webhook for video: {video_id}"
```

## Troubleshooting

### Issue: Webhook Not Receiving Data

**Symptoms:**
- Video marked as "processing" but never completes
- No webhook logs in application

**Solutions:**
1. Verify webhook URL is publicly accessible (HTTPS required)
2. Check Bright Data dashboard for webhook delivery status
3. Verify `WEBHOOK_AUTH_SECRET` matches in both places
4. Check firewall/security settings allow incoming POST requests
5. Review Bright Data webhook logs in dashboard

### Issue: Authentication Errors

**Symptoms:**
- `401 Unauthorized` in webhook logs
- "Invalid or missing webhook signature" error

**Solutions:**
1. Verify `WEBHOOK_AUTH_SECRET` is set correctly
2. Check that Bright Data is sending `Authorization: Bearer {secret}` header
3. Ensure secret doesn't have extra spaces or quotes

### Issue: Missing Transcript

**Symptoms:**
- Webhook received but transcript is empty
- "Missing required fields" error

**Solutions:**
1. Verify scraper is configured to extract transcripts
2. Check if video has captions/transcripts available
3. Review raw webhook payload in logs (`raw_response` field)
4. Some videos may not have transcripts available

### Issue: API Request Fails

**Symptoms:**
- "Failed to start transcript extraction" error
- HTTP errors when triggering extraction

**Solutions:**
1. Verify `BRIGHT_DATA_API_KEY` is correct
2. Check API key has necessary permissions
3. Verify `BRIGHT_DATA_COLLECTOR_ID` or `BRIGHT_DATA_DATASET_ID` is correct
4. Check API rate limits in Bright Data dashboard
5. Review API response in logs for specific error messages

### Issue: Wrong API Type

**Symptoms:**
- "Collector ID not configured" or "Dataset ID not configured" errors

**Solutions:**
1. Set `BRIGHT_DATA_API_TYPE=scraper` for Web Scraper API
2. Set `BRIGHT_DATA_API_TYPE=dataset` for Datasets API
3. Ensure corresponding ID is set (`COLLECTOR_ID` or `DATASET_ID`)

## Webhook Payload Examples

### Successful Webhook Payload

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Example Video Title",
  "transcript": "This is the full transcript of the video...",
  "formatted_transcript": "This is the formatted transcript...",
  "video_length": 240,
  "preview_image": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
  "date_posted": "2024-01-15T10:30:00Z",
  "youtuber": "@examplechannel",
  "channel_url": "https://www.youtube.com/@examplechannel",
  "views": 1000000,
  "likes": 50000,
  "subscribers": 100000,
  "description": "Video description..."
}
```

### Error Response Format

If webhook processing fails, the endpoint returns:

```json
{
  "status": "error",
  "message": "Error description"
}
```

## Additional Resources

- [Bright Data YouTube API Documentation](https://docs.brightdata.com/scraping-automation/web-scraper-api/social-media-apis/youtube)
- [Bright Data Webhook Documentation](https://docs.brightdata.com/scraping-automation/web-scraper-api/webhooks)
- [Bright Data API Reference](https://docs.brightdata.com/api-reference)

## Support

If you encounter issues:

1. Check application logs for detailed error messages
2. Review Bright Data dashboard for API/webhook status
3. Verify all environment variables are set correctly
4. Test webhook endpoint with a tool like Postman
5. Contact Bright Data support for API-specific issues

---

**Last Updated:** 2024-01-15
**Version:** 1.0


