# Bright Data Webhook Configuration & Testing Guide

## Do You Need to Configure Webhook in Bright Data Dashboard?

### Short Answer: **NOT REQUIRED, but recommended**

Since our code **passes the webhook URL in each API request** (via the `endpoint` parameter), you don't strictly need to configure it in the Bright Data dashboard. However, setting a default webhook in the dashboard is recommended as a backup.

### How It Works

Our code sends the webhook URL with every API request:
```python
request_params = {
    "endpoint": webhook_url,  # ← Sent with each request
    "format": "json",
    "auth_header": f"Bearer {webhook_secret}"
}
```

So Bright Data knows where to send the data **per-request**, not from a global setting.

### Optional: Set Default Webhook in Dashboard

If you want to set a default webhook (optional but recommended):

1. Go to: `https://brightdata.com/cp/scrapers/api/gd_lk56epmy2i5g7lzu0k/pdp/overview?id=hl_81577a46`
2. Click **Management API** tab
3. Look for **Delivery option** or **Webhook** settings
4. Set default webhook URL (if available)
5. This acts as a fallback if `endpoint` parameter is missing

**Note**: Our code always sends the `endpoint` parameter, so this is just a safety net.

---

## Testing the Webhook Setup

### Step 1: Test Your Webhook Endpoint Directly

First, verify your webhook endpoint is accessible and working:

```bash
# Test webhook endpoint with a sample payload
curl -X POST https://your-domain.com/api/webhooks/brightdata \
  -H "Authorization: Bearer YOUR_WEBHOOK_AUTH_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "dQw4w9WgXcQ",
    "title": "Test Video",
    "transcript": "This is a test transcript to verify the webhook is working.",
    "video_length": 240,
    "youtuber": "@testchannel",
    "views": 1000,
    "likes": 50
  }'
```

**Expected Response**: `{"status": "success"}`

If you get an error, check:
- Is the endpoint publicly accessible?
- Is HTTPS working?
- Is `WEBHOOK_AUTH_SECRET` set correctly?

### Step 2: Test Locally with ngrok (For Development)

If testing locally, use ngrok to expose your local server:

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000
```

This gives you a public URL like: `https://abc123.ngrok.io`

Then:
1. Set `API_BASE_URL=https://abc123.ngrok.io` in your `.env`
2. Test the webhook with the ngrok URL

### Step 3: Test Full Flow - Trigger Bright Data API

#### Option A: Test via Your Application

1. Start your Flask app:
   ```bash
   python app.py
   ```

2. Make a request to summarize a video:
   ```bash
   curl -X POST http://localhost:5000/summarize \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_USER_TOKEN" \
     -d '{"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
   ```

3. Check your application logs for:
   - `"Triggering Bright Data extraction for video: ..."`
   - `"Bright Data API Response Status: ..."`
   - `"--- BRIGHT DATA WEBHOOK RECEIVED ---"` (when webhook arrives)

#### Option B: Test Bright Data API Directly

Test the API call directly to see the response:

```bash
curl -X POST "https://api.brightdata.com/scrapers/v1/collector/hl_81577a46/trigger?endpoint=https://your-domain.com/api/webhooks/brightdata&format=json&auth_header=Bearer%20YOUR_WEBHOOK_SECRET" \
  -H "Authorization: Bearer YOUR_BRIGHT_DATA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }'
```

**Expected Response**:
```json
{
  "snapshot_id": "s_...",
  "status": "running"
}
```

### Step 4: Monitor in Bright Data Dashboard

1. Go to your scraper page
2. Click **Log** tab
3. You should see:
   - API requests you made
   - Status of each request
   - Webhook delivery status (if available)

### Step 5: Check Application Logs

Watch your application logs for:

```python
# When triggering extraction:
logger.info("Triggering Bright Data extraction for video: ...")
logger.info("Bright Data API Response Status: 200")

# When webhook is received:
logger.info("--- BRIGHT DATA WEBHOOK RECEIVED ---")
logger.info("Processing webhook for video: ...")
logger.info("Successfully processed webhook for video: ...")
```

### Step 6: Verify Database Update

Check your Firestore database:

1. Go to `videos` collection
2. Find the video document by video_id
3. Verify:
   - `status` is `"completed"`
   - `transcript` field has content
   - `summary` field is generated
   - `updated_at` timestamp is recent

---

## Troubleshooting Tests

### Issue: Webhook Not Receiving Data

**Symptoms**: API call succeeds but no webhook received

**Solutions**:
1. Check if webhook URL is publicly accessible:
   ```bash
   curl https://your-domain.com/api/webhooks/brightdata
   # Should return something (even if 405 Method Not Allowed)
   ```

2. Verify `API_BASE_URL` is set correctly:
   ```bash
   echo $API_BASE_URL  # Should be your public domain
   ```

3. Check Bright Data logs in dashboard for delivery errors

4. Test webhook endpoint manually (Step 1 above)

### Issue: Authentication Error

**Symptoms**: `401 Unauthorized` in webhook logs

**Solutions**:
1. Verify `WEBHOOK_AUTH_SECRET` matches:
   ```bash
   # In your app
   echo $WEBHOOK_AUTH_SECRET
   
   # In Bright Data request (check logs)
   # Should match exactly
   ```

2. Test with correct header:
   ```bash
   curl -X POST https://your-domain.com/api/webhooks/brightdata \
     -H "Authorization: Bearer YOUR_EXACT_SECRET" \
     ...
   ```

### Issue: API Request Fails

**Symptoms**: Error when calling Bright Data API

**Solutions**:
1. Verify API key:
   ```bash
   echo $BRIGHT_DATA_API_KEY
   # Should be your Bright Data API key
   ```

2. Check collector ID:
   ```bash
   echo $BRIGHT_DATA_COLLECTOR_ID
   # Should be: hl_81577a46
   ```

3. Check API response in logs for specific error message

### Issue: Transcript Missing

**Symptoms**: Webhook received but transcript is empty

**Solutions**:
1. Check if video has captions available on YouTube
2. Review `raw_response` in webhook logs
3. Some videos may not have transcripts

---

## Quick Test Checklist

- [ ] Webhook endpoint is publicly accessible (HTTPS)
- [ ] `WEBHOOK_AUTH_SECRET` is set and matches
- [ ] `BRIGHT_DATA_API_KEY` is set correctly
- [ ] `BRIGHT_DATA_COLLECTOR_ID` is set to `hl_81577a46`
- [ ] `API_BASE_URL` points to your public domain
- [ ] Test webhook endpoint directly (Step 1) - works
- [ ] Test Bright Data API call (Step 3) - returns snapshot_id
- [ ] Check application logs - webhook received
- [ ] Check Firestore - video document updated with transcript

---

## Environment Variables Summary

Make sure these are set:

```bash
# Required
BRIGHT_DATA_API_KEY=your_api_key
BRIGHT_DATA_COLLECTOR_ID=hl_81577a46
BRIGHT_DATA_API_TYPE=scraper
API_BASE_URL=https://your-production-domain.com
WEBHOOK_AUTH_SECRET=your_secure_random_string

# Optional (for legacy API)
BRIGHT_DATA_DATASET_ID=gd_lk56epmy2i5g7lzu0k
```

---

## Next Steps After Testing

Once everything is working:

1. ✅ Webhook receives data correctly
2. ✅ Transcript is parsed and stored
3. ✅ Summary is generated
4. ✅ Database is updated
5. ✅ User usage is tracked

You're ready for production! 🎉


