# NotoAI - YouTube Video Summarization App

NotoAI is a powerful web application that allows users to convert YouTube videos into concise, structured notes using AI. Save hours by automatically extracting key insights from any YouTube video with transcripts available.

## Features

- **YouTube Transcript Extraction**: Automatically extract transcripts from any YouTube video
- **AI-Powered Summarization**: Generate structured notes with key points using OpenAI's GPT models
- **Tiered Subscription Plans**: 
  - Free: 30 minutes/month with basic summaries
  - Pro (₹299/month): 300 minutes/month with premium structured notes
  - Elite (₹799/month): 1000 minutes/month with premium notes and priority processing
- **Razorpay Payment Integration**: Secure subscription management with Indian payment gateway
- **Usage Tracking**: Monitor your monthly usage and plan limits
- **Firebase Authentication**: Secure login with email or Google account
- **Firestore Database**: Cloud storage for user data, summaries, and usage metrics
- **Responsive Dark UI**: Beautiful modern interface with luxury dark mode

## Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or later
- pip (Python package installer)
- A Firebase account
- OpenAI API key
- YouTube Data API key
- Razorpay account (for payment integration)

## Getting Started

To get a local copy up and running follow these simple steps.

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ytnotes-app
cd ytnotes-app
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configuration

#### Firebase Setup 
- Create a Firebase account (https://firebase.google.com/)
- Go to the Firebase Console and add a new project
- Add a web app to your project
- Go to "Project Settings" > Scroll to "SDK setup and configuration" > Select "Config" radio button and copy the "firebaseConfig" data
- Paste the "firebaseConfig" data into `static/firebase-config.js` file
- Navigate to the "Firestore Database" section and create your database in test mode
- Go to "Project Settings" > "Service accounts" > "Firebase Admin SDK" > Python option > click "Generate new private key" > Download the JSON file
- Place the downloaded JSON file in your project directory and rename it to `firebase-auth.json`
- Navigate to "Build" > "Authentication" section > click "Sign-in Method" and enable sign-in for Email/Password and Google options

#### API Keys and Environment Variables
Create a `.env` file in the root directory by copying the `.env.example` file and fill in the required API keys:

```
# Flask Secret Key (generate a random string)  
SECRET_KEY=your_secure_secret_key_here

# OpenAI API Key for summarization
OPENAI_API_KEY=your_openai_api_key_here

# YouTube API Key for video details
YOUTUBE_API_KEY=your_youtube_api_key_here

# Razorpay Payment Integration
RAZORPAY_KEY_ID=your_razorpay_key_id_here
RAZORPAY_KEY_SECRET=your_razorpay_key_secret_here
```

- To get an OpenAI API key, sign up at https://platform.openai.com/
- To get a YouTube API key, go to Google Cloud Console, create a project, enable the YouTube Data API v3, and create an API key
- For Razorpay integration, sign up at https://razorpay.com/ and get your API keys from the dashboard

### 4. Firestore Database Structure

The application uses the following Firestore collections:

- `users`: Stores user information, subscription details, and usage statistics
  - User document fields include:
    - `subscription`: Information about the user's plan type, status, and billing dates
    - `usage`: Tracking of minutes used and video history
    - `profile`: User profile information

### 5. Run the application

```bash
python app.py
```

This will start the Flask application on http://localhost:5000 by default.

### 6. Using the Application

1. Sign up for an account using email or Google authentication
2. Navigate to the dashboard and paste a YouTube URL in the input field
3. Click "Summarize" to extract the transcript and generate notes
4. View your summary and save it for future reference
5. Upgrade your plan via the Pricing page if you need more minutes



## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are greatly appreciated.

Fork the Project
Create your Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add some AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request

## License
Distributed under the MIT License. 



## Acknowledgements
Flask
Firebase






# flask-firebase-auth-template
# flask-firebase-auth-template
