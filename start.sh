#!/bin/bash

echo "Starting RAG Dashboard API..."
echo "=============================="

if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please run ./setup_firebase.sh to configure your Firebase credentials."
    exit 1
fi

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting application..."
python manage.py