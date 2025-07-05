# Railway Deployment Guide for Noto MVP

This guide will walk you through deploying your Noto MVP Flask application on Railway.

## Prerequisites

1. A Railway account (sign up at https://railway.app)
2. Railway CLI installed (optional, but recommended)
3. Git repository with your code
4. All required API keys and credentials

## Step 1: Prepare Your Repository

Ensure you have the following files in your repository:

### Required Files Created:
- ✅ `Procfile` - Tells Railway how to run your app
- ✅ `railway.json` - Railway-specific configuration
- ✅ `runtime.txt` - Specifies Python version
- ✅ `requirements.txt` - Already exists with dependencies
- ✅ `.env.example` - Template for environment variables

## Step 2: Push to GitHub

1. Initialize git (if not already done):
```bash
git init
git add .
git commit -m "Prepare for Railway deployment"
```

2. Create a new repository on GitHub and push your code:
```bash
git remote add origin https://github.com/YOUR_USERNAME/noto-mvp.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy on Railway

### Option A: Deploy via Railway Dashboard (Recommended)

1. Go to https://railway.app and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account if not already connected
5. Select your `noto-mvp` repository
6. Railway will automatically detect your Flask app and start deployment

### Option B: Deploy via Railway CLI

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login to Railway:
```bash
railway login
```

3. Initialize a new project:
```bash
railway init
```

4. Link to your GitHub repo:
```bash
railway link
```

5. Deploy:
```bash
railway up
```

## Step 4: Configure Environment Variables

After deployment, you need to set up your environment variables in Railway:

1. In your Railway project dashboard, go to the "Variables" tab
2. Click "Add Variable" and add each of the following:

### Required Environment Variables:

```
# Flask Configuration
SECRET_KEY=<generate-a-secure-random-string>

# API Keys
OPENAI_API_KEY=<your-openai-api-key>
YOUTUBE_API_KEY=<your-youtube-api-key>

# Payment Integration (if using Razorpay)
RAZORPAY_KEY_ID=<your-razorpay-key-id>
RAZORPAY_KEY_SECRET=<your-razorpay-key-secret>

# Firebase Configuration
FIREBASE_PROJECT_ID=<your-firebase-project-id>
FIREBASE_PRIVATE_KEY_ID=<your-firebase-private-key-id>
FIREBASE_PRIVATE_KEY=<your-firebase-private-key>
FIREBASE_CLIENT_EMAIL=<your-firebase-client-email>
FIREBASE_CLIENT_ID=<your-firebase-client-id>
FIREBASE_CLIENT_CERT_URL=<your-firebase-client-cert-url>

# Bright Data Configuration (if applicable)
BRIGHT_DATA_AUTH_TOKEN=<your-bright-data-auth-token>
BRIGHT_DATA_DATASET_ID=<your-bright-data-dataset-id>
```

### Important Notes for Environment Variables:

1. **SECRET_KEY**: Generate a secure random string:
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```

2. **FIREBASE_PRIVATE_KEY**: This is a multi-line JSON key. In Railway, you need to:
   - Copy the entire private key including `\n` characters
   - Wrap it in quotes if it contains special characters
   - Or base64 encode it and decode in your app

3. **Production Settings**: Railway automatically sets:
   - `PORT` - The port your app should listen on
   - `RAILWAY_ENVIRONMENT` - Set to "production"

## Step 5: Configure Custom Domain (Optional)

1. In your Railway project, go to "Settings"
2. Under "Domains", click "Generate Domain" for a free Railway subdomain
3. Or click "Add Custom Domain" to use your own domain
4. Update your DNS records as instructed

## Step 6: Set Up Database (If Needed)

If you need a PostgreSQL database:

1. In your Railway project, click "New Service"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically set the `DATABASE_URL` environment variable

## Step 7: Monitor and Debug

### View Logs:
- Dashboard: Click on your service → "Logs" tab
- CLI: `railway logs`

### Common Issues and Solutions:

1. **Module Import Errors**: Ensure all dependencies are in `requirements.txt`
2. **Port Binding Error**: Make sure you're using `$PORT` environment variable
3. **Static Files Not Loading**: Check that Flask is configured to serve static files
4. **Session Issues**: Ensure `SESSION_COOKIE_SECURE` is True for HTTPS

### Debug Commands:
```bash
# View deployment logs
railway logs

# Open a shell in your deployed app
railway run bash

# Check environment variables
railway variables
```

## Step 8: Production Considerations

1. **Disable Debug Mode**: Ensure `app.run(debug=False)` in production
2. **Use Gunicorn**: Already configured in Procfile
3. **Set Up Monitoring**: Consider adding error tracking (e.g., Sentry)
4. **Configure CORS**: Update allowed origins for production domain
5. **SSL/HTTPS**: Railway provides SSL certificates automatically

## Step 9: Continuous Deployment

Railway automatically deploys when you push to your connected GitHub branch:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

## Troubleshooting

### If deployment fails:

1. Check build logs in Railway dashboard
2. Verify all environment variables are set
3. Ensure `requirements.txt` is up to date
4. Check Python version compatibility

### If app crashes after deployment:

1. Check runtime logs: `railway logs`
2. Verify Firebase credentials are correct
3. Ensure all API keys are valid
4. Check if port binding is correct

## Additional Resources

- Railway Documentation: https://docs.railway.app
- Railway Discord Community: https://discord.gg/railway
- Flask Deployment Guide: https://flask.palletsprojects.com/en/2.3.x/deploying/

## Support

If you encounter issues:
1. Check Railway status page: https://status.railway.app
2. Review logs carefully for error messages
3. Join Railway Discord for community support
4. Check your application logs for specific errors

---

**Note**: Remember to never commit sensitive information like API keys to your repository. Always use environment variables for secrets.
