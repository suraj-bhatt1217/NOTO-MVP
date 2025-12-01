# Quick Start Guide

## How to Start the App

### Step 0: Activate Virtual Environment (IMPORTANT!)

**If you're using a virtual environment, activate it first:**

#### Windows (PowerShell):
```bash
.\venv\Scripts\Activate.ps1
```

#### Windows (CMD):
```bash
venv\Scripts\activate.bat
```

#### Mac/Linux:
```bash
source venv/bin/activate
```

**If you don't have a virtual environment yet, create one:**

#### Windows:
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Mac/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 1: Install Dependencies

Once your virtual environment is activated, install all required packages:

```bash
pip install -r requirements.txt
```

**Note**: If you get permission errors on Windows, use:
```bash
pip install -r requirements.txt --user
```

### Step 2: Set Up Environment Variables

Create a `.env` file in the root directory with your API keys:

```bash
# Copy this template and fill in your values
# Flask Secret Key (generate a random string)
SECRET_KEY=your_secure_secret_key_here

# OpenAI API Key for summarization
OPENAI_API_KEY=your_openai_api_key_here

# YouTube API Key for video details
YOUTUBE_API_KEY=your_youtube_api_key_here

# Razorpay Payment Integration (optional for testing)
RAZORPAY_KEY_ID=your_razorpay_key_id_here
RAZORPAY_KEY_SECRET=your_razorpay_key_secret_here

# Bright Data Configuration (for YouTube transcript processing)
BRIGHT_DATA_API_KEY=your_bright_data_api_key_here
BRIGHT_DATA_API_TYPE=scraper
BRIGHT_DATA_COLLECTOR_ID=hl_81577a46
API_BASE_URL=http://localhost:5000  # For local testing
WEBHOOK_AUTH_SECRET=your_secure_webhook_secret_here

# Firebase Configuration (from firebase-auth.json - these are set via environment or JSON file)
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=your_client_email
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CLIENT_CERT_URL=your_cert_url
```

**Quick way to generate SECRET_KEY:**
```python
import secrets
print(secrets.token_hex(32))
```

### Step 3: Configure Firebase

1. Make sure you have `firebase-auth.json` in the root directory (or set Firebase env vars)
2. Update `static/firebase-config.js` with your Firebase web app config

### Step 4: Start the Application

**Make sure your virtual environment is activated!** You should see `(venv)` in your terminal prompt.

#### Option A: Simple Start (Development)
```bash
python app.py
```

The app will start on **http://localhost:5000**

#### Option B: Using Flask CLI (Recommended)
```bash
flask run
```

Or specify a different port:
```bash
flask run --port 5000
```

#### Option C: Production Mode (with Gunicorn)
```bash
gunicorn app:app
```

**Note**: If you see "module not found" errors, make sure:
1. Virtual environment is activated (you should see `(venv)` in prompt)
2. Dependencies are installed: `pip install -r requirements.txt`

### Step 5: Access the Application

Open your browser and go to:
```
http://localhost:5000
```

## Troubleshooting

### Issue: Module not found errors

**Solution**: Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

If `httpx` is missing (for Bright Data), install it:
```bash
pip install httpx
```

### Issue: Firebase authentication errors

**Solution**: 
- Check that `firebase-auth.json` exists and is valid
- Or set all `FIREBASE_*` environment variables in `.env`

### Issue: Port already in use

**Solution**: Use a different port:
```bash
flask run --port 5001
```

Or find and kill the process using port 5000:
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:5000 | xargs kill
```

### Issue: Environment variables not loading

**Solution**: 
- Make sure `.env` file is in the root directory (same folder as `app.py`)
- Check that `python-dotenv` is installed: `pip install python-dotenv`

### Issue: Bright Data webhook not working locally

**Solution**: Use ngrok to expose your local server:
```bash
# Install ngrok from https://ngrok.com
ngrok http 5000

# Then update API_BASE_URL in .env to the ngrok URL
API_BASE_URL=https://abc123.ngrok.io
```

## Testing the Setup

### 1. Test Webhook Endpoint
```bash
python test_webhook.py
```

### 2. Test the App
1. Start the app: `python app.py`
2. Open http://localhost:5000
3. Sign up or log in
4. Try summarizing a YouTube video

## Development vs Production

### Development Mode
- Debug mode enabled
- Auto-reload on code changes
- Detailed error messages
- Start with: `python app.py` or `flask run`

### Production Mode
- Debug mode disabled
- Use Gunicorn or similar WSGI server
- Set `FLASK_ENV=production`
- See `RAILWAY_DEPLOYMENT_GUIDE.md` for deployment

## Next Steps

1. ✅ App is running
2. ⏳ Test webhook: `python test_webhook.py`
3. ⏳ Test with a real YouTube video
4. ⏳ Check logs for any errors

---

**Need help?** Check:
- `README.md` - Full setup instructions
- `BRIGHT_DATA_WEBHOOK_SETUP.md` - Bright Data configuration
- `BRIGHT_DATA_WEBHOOK_CONFIGURATION.md` - Testing guide

