import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add current directory to path so we can import apps
sys.path.append(os.getcwd())

from manage import app
from core.middleware import verify_firebase_token
from apps.documents.service import document_service

client = TestClient(app)

def test_upload_questions_json():
    # Mock authentication
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test_user"}
    
    try:
        # Prepare file
        json_path = "tests/sample_questions.json"
        with open(json_path, "rb") as f:
            files = {"file": ("sample_questions.json", f, "application/json")}
            response = client.post("/api/v1/documents/questions/upload", files=files)
            
        print("Response status:", response.status_code)
        print("Response body:", response.json())
        
        assert response.status_code == 200
        data = response.json()
        assert "inserted_count" in data
        assert data["inserted_count"] == 2
        
        # Verify in MongoDB
        count = document_service.questions_collection.count_documents({"subject": {"$in": ["Chemistry", "Physics"]}})
        print(f"Verified {count} documents in MongoDB")
        assert count >= 2
        
        # Check a document has embedding
        doc = document_service.questions_collection.find_one({"subject": "Chemistry"})
        assert doc is not None
        assert "embedding" in doc
        assert len(doc["embedding"]) == 384 # Expected length for all-MiniLM-L6-v2
        
    finally:
        app.dependency_overrides = {}

if __name__ == "__main__":
    test_upload_questions_json()
