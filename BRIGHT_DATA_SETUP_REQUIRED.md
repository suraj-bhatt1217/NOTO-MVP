# Bright Data Setup Required

## Current Status: ❌ NOT CONFIGURED

Your app is showing the error: **"Bright Data not configured"**

This means you need to add Bright Data credentials to your `.env` file.

## Quick Fix

Add these lines to your `.env` file:

```bash
# Bright Data Configuration
BRIGHT_DATA_API_KEY=your_bright_data_api_key_here
BRIGHT_DATA_API_TYPE=scraper
BRIGHT_DATA_COLLECTOR_ID=hl_81577a46
# OR use dataset ID instead:
# BRIGHT_DATA_DATASET_ID=gd_lk56epmy2i5g7lzu0k

# Webhook Configuration (for receiving transcript data)
API_BASE_URL=http://localhost:5000  # For local testing, use ngrok for production
WEBHOOK_AUTH_SECRET=your_secure_random_string_here
```

## How to Get Your Bright Data API Key

1. Go to your Bright Data dashboard: https://brightdata.com
2. Navigate to **Account Settings** → **API**
3. Generate or copy your **API Key** (also called Auth Token)
4. Copy it to `BRIGHT_DATA_API_KEY` in your `.env` file

## Your Bright Data Identifiers

From your dashboard URL, you have:
- **Dataset ID**: `gd_lk56epmy2i5g7lzu0k`
- **Collector ID**: `hl_81577a46`

You can use either:
- `BRIGHT_DATA_COLLECTOR_ID=hl_81577a46` (recommended for Web Scraper API)
- OR `BRIGHT_DATA_DATASET_ID=gd_lk56epmy2i5g7lzu0k` (for Datasets API)

## Generate Webhook Secret

Run this in Python to generate a secure secret:

```python
import secrets
print(secrets.token_hex(32))
```

Or use:
```bash
# Windows PowerShell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# Or just use a random string
```

## After Adding to .env

1. **Restart your Flask app** (stop and start again)
2. The app will now be able to trigger Bright Data transcript extraction
3. Test by submitting a YouTube video URL

## Testing

After setting up, test with:
```bash
python test_webhook.py
```

This will verify your configuration is correct.

---

**Note**: If you're testing locally, you'll need to use ngrok to expose your local server so Bright Data can send webhooks:

```bash
# Install ngrok from https://ngrok.com
ngrok http 5000

# Then update API_BASE_URL in .env to the ngrok URL
API_BASE_URL=https://abc123.ngrok.io
```



