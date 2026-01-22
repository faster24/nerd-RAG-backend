# 🤖 RAG Dashboard API

FastAPI-based web service with Firebase authentication and role-based access control.

## Quick Start

```bash
# Clone and setup
git clone <your-repo-url>
cd nerd_dashboard

# Create virtual environment with Python 3.10
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally
python manage.py

# Or with Docker
docker-compose up --build
```

API available at `http://localhost:8000`

## Documentation

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI Spec: `http://localhost:8000/openapi.json`

## Requirements

- Python 3.10 or 3.11
- Firebase credentials (`firebase_credential.json`)
- Docker (optional)

## License

MIT
