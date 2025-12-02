# Bright Data Webhook Implementation - Findings & Requirements

Based on exploring the Bright Data dashboard, here's what needs to be configured:

## Key Identifiers from Your Bright Data Account

From the URL `https://brightdata.com/cp/scrapers/api/gd_lk56epmy2i5g7lzu0k/pdp/overview?nav_from=my_scrapers&id=hl_81577a46`:

- **Dataset ID**: `gd_lk56epmy2i5g7lzu0k`
- **Collector ID**: `hl_81577a46`

## What You Need to Do

### 1. Configure Webhook in Bright Data Dashboard

1. Go to your scraper page: `https://brightdata.com/cp/scrapers/api/gd_lk56epmy2i5g7lzu0k/pdp/overview?id=hl_81577a46`
2. Navigate to **Management API** tab
3. Look for **Delivery option** section
4. Configure webhook delivery:
   - Select **Webhook** as delivery method
   - Enter your webhook URL: `https://your-domain.com/api/webhooks/brightdata`
   - Set authentication header: `Bearer {WEBHOOK_AUTH_SECRET}`
   - Format: JSON
   - Enable uncompressed webhook (if available)

### 2. Set Environment Variables

Add these to your `.env` file or deployment platform:

```bash
# Bright Data Configuration
BRIGHT_DATA_API_KEY=your_api_key_here
BRIGHT_DATA_API_TYPE=scraper  # Use 'scraper' for Web Scraper API
BRIGHT_DATA_COLLECTOR_ID=hl_81577a46  # Your collector ID
BRIGHT_DATA_DATASET_ID=gd_lk56epmy2i5g7lzu0k  # Your dataset ID (may not be needed for scraper API)

# Webhook Configuration
API_BASE_URL=https://your-production-domain.com  # Your public domain
WEBHOOK_AUTH_SECRET=your_secure_random_string  # Generate with: openssl rand -hex 32
```

### 3. Get Your API Key

1. In Bright Data dashboard, go to **Account Settings** → **API**
2. Generate or copy your API key
3. Add it to `BRIGHT_DATA_API_KEY` environment variable

## What the Code Does

### Current Implementation

The code is already set up to:

1. **Trigger Extraction** (`services/bright_data.py`):
   - Makes POST request to Bright Data API
   - Sends YouTube video URL
   - Includes webhook URL in request parameters
   - Returns snapshot/job ID

2. **Receive Webhook** (`app.py` - `/api/webhooks/brightdata`):
   - Validates webhook authentication
   - Parses incoming transcript data
   - Updates video document in Firestore
   - Generates summary using OpenAI
   - Updates user usage statistics

### API Endpoint Format

For **Web Scraper API** (recommended):
```
POST https://api.brightdata.com/scrapers/v1/collector/{collector_id}/trigger
```

Request format:
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

Query parameters:
- `endpoint`: Your webhook URL
- `format`: `json`
- `auth_header`: `Bearer {WEBHOOK_AUTH_SECRET}` (optional but recommended)

## Testing Steps

1. **Test Webhook Endpoint**:
   ```bash
   curl -X POST https://your-domain.com/api/webhooks/brightdata \
     -H "Authorization: Bearer YOUR_WEBHOOK_SECRET" \
     -H "Content-Type: application/json" \
     -d '{"video_id": "test123", "transcript": "test transcript"}'
   ```

2. **Trigger a Test Extraction**:
   - Use the `/summarize` endpoint in your app
   - Submit a YouTube video URL
   - Check logs for API call and webhook receipt

3. **Monitor in Bright Data Dashboard**:
   - Check the **Log** tab for API requests
   - Verify webhook delivery status

## Important Notes

1. **HTTPS Required**: Webhook URL must be HTTPS (not HTTP)
2. **Public Access**: Your webhook endpoint must be publicly accessible
3. **Authentication**: Always use `WEBHOOK_AUTH_SECRET` to secure your webhook
4. **Collector ID vs Dataset ID**: 
   - Use `BRIGHT_DATA_COLLECTOR_ID` for Web Scraper API
   - Use `BRIGHT_DATA_DATASET_ID` for legacy Datasets API
   - Set `BRIGHT_DATA_API_TYPE=scraper` for Web Scraper API

## Troubleshooting

If webhooks aren't working:

1. **Check Webhook URL**: Must be publicly accessible HTTPS
2. **Verify Authentication**: `WEBHOOK_AUTH_SECRET` must match in both places
3. **Check Bright Data Logs**: Dashboard → Log tab shows delivery status
4. **Review Application Logs**: Look for webhook receipt messages
5. **Test Webhook Manually**: Use curl to test your endpoint directly

## Next Steps

1. ✅ Code is already implemented
2. ⏳ Configure webhook in Bright Data dashboard
3. ⏳ Set environment variables
4. ⏳ Test with a real YouTube video
5. ⏳ Monitor logs for any issues

---

**Last Updated**: Based on Bright Data dashboard exploration
**Collector ID**: `hl_81577a46`
**Dataset ID**: `gd_lk56epmy2i5g7lzu0k`



