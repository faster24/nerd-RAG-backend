# 🤖 RAG Dashboard API

Welcome to the RAG Dashboard API! This is a FastAPI-based web service that handles user authentication using Firebase.

## 🛠️ Quick Setup (3 Easy Steps)

### Step 1: Get the Code
```bash
git clone <your-repo-url>
cd nerd_dashboard
```

### Step 2: Install Dependencies
```bash
# For beginners - use the virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Run the App
```bash
# Simple way
python manage.py

# Or with Docker (recommended)
docker-compose up --build
```

That's it! 🎉 Your API will be running at `http://localhost:8000`

## 📋 Detailed Setup Guide

### Option A: Using Docker (Easiest for Beginners)

Docker is like a "magic box" that contains everything your app needs.

1. **Install Docker** from https://docker.com

2. **Make sure you have your Firebase credentials**:
   - Place `firebase_credential.json` in the project root
   - This file comes from Firebase Console

3. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

4. **Check if it's working**:
   - Open `http://localhost:8000` in your browser
   - You should see: `{"name":"NERD_Dashboard","version":"1.0.0","status":"running"}`

### Option B: Manual Setup (For Learning)

If you want to understand how everything works:

1. **Install Python 3.10** (if you don't have it)

2. **Create a virtual environment** (like a clean room for your project):
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OR on Windows: venv\Scripts\activate
   ```

3. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Firebase** (see below)

5. **Run the app**:
   ```bash
   python manage.py
   ```

## 🔥 Setting Up Firebase (Important!)

Firebase is Google's authentication service.

### Step 1: Create Firebase Project
1. Go to https://console.firebase.google.com/
2. Click "Create a project"
3. Name it something like "rag-dashboard"
4. Follow the setup wizard

### Step 2: Enable Authentication
1. In your Firebase project, go to "Authentication"
2. Click "Get started"
3. Go to "Sign-in method" tab
4. Enable "Email/Password" sign-in method

### Step 3: Get Service Account Key
1. In Firebase Console, go to "Project settings" (gear icon)
2. Go to "Service accounts" tab
3. Click "Generate new private key"
4. Download the JSON file
5. Rename it to `firebase_credential.json`
6. Place it in your project root folder

### Step 4: Update .env File
Your `.env` file should look like this:
```bash
# App settings
APP_NAME=NERD Dashboard
DEBUG=True

# Server
HOST=0.0.0.0
PORT=8000

# Firebase (you don't need to change these if using firebase_credential.json)
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_API_KEY=your-api-key

# Security
JWT_SECRET_KEY=your-secret-key-here
```

## 🧪 Testing Your API

### Using the Web Interface (Easiest)
1. Open `http://localhost:8000/docs` in your browser
2. You'll see all available API endpoints with Swagger UI
3. Click on any endpoint to test it
4. Click "Try it out" and fill in the data

### Using Command Line
```bash
# Test if API is running
curl http://localhost:8000/

# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## 📚 Learning Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Firebase Auth**: https://firebase.google.com/docs/auth
- **Python Virtual Environments**: https://docs.python.org/3/tutorial/venv.html
- **Docker Basics**: https://docker.com/get-started
- **Pydantic v2**: https://docs.pydantic.dev/latest/

## 🤝 Contributing

1. Create a new branch for your changes
2. Make your changes
3. Test everything works
4. Create a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

**Need help?** Check the `/docs` endpoint for interactive API documentation!
