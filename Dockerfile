FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make sure the app can read the Firebase credentials
RUN chmod 644 firebase_credential.json

EXPOSE 8000

CMD ["uvicorn", "manage:app", "--host", "0.0.0.0", "--port", "8000"]