#!/bin/bash

echo "Firebase Setup Helper"
echo "===================="
echo ""
echo "This script will help you set up your Firebase credentials."
echo ""
echo "Prerequisites:"
echo "1. Create a Firebase project at https://console.firebase.google.com/"
echo "2. Enable Email/Password authentication in Firebase Console"
echo "3. Create a service account and download the JSON key"
echo "4. Enable the Identity Toolkit API in Google Cloud Console"
echo ""
read -p "Have you completed all prerequisites? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please complete the prerequisites first."
    exit 1
fi

echo ""
echo "Please enter the following information from your Firebase service account JSON:"
echo ""

read -p "Firebase Project ID: " firebase_project_id
read -p "Firebase Private Key (paste the entire key including quotes): " firebase_private_key
read -p "Firebase Client Email: " firebase_client_email
read -p "Firebase API Key: " firebase_api_key
read -p "Firebase Auth Domain (e.g., project-id.firebaseapp.com): " firebase_auth_domain

echo ""
echo "Updating .env file..."

sed -i.bak "s/FIREBASE_PROJECT_ID=/FIREBASE_PROJECT_ID=$firebase_project_id/" .env
sed -i.bak "s/FIREBASE_PRIVATE_KEY=/FIREBASE_PRIVATE_KEY=$firebase_private_key/" .env
sed -i.bak "s/FIREBASE_CLIENT_EMAIL=/FIREBASE_CLIENT_EMAIL=$firebase_client_email/" .env
sed -i.bak "s/FIREBASE_API_KEY=/FIREBASE_API_KEY=$firebase_api_key/" .env
sed -i.bak "s/FIREBASE_AUTH_DOMAIN=/FIREBASE_AUTH_DOMAIN=$firebase_auth_domain/" .env

echo ""
echo "Setup complete! Your .env file has been updated."
echo ""
echo "Next steps:"
echo "1. Review the .env file to ensure all values are correct"
echo "2. Run 'pip install -r requirements.txt' to install dependencies"
echo "3. Run 'python manage.py' to start the application"
echo "4. Visit http://localhost:8000/docs for API documentation"