import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from manage import app
from apps.chat.service import chat_service

client = TestClient(app)

def test_chat_endpoint_logic():
    # We want to test the endpoint and the service logic
    # Mock the LLM to avoid needing a real API key
    from langchain_core.messages import AIMessage
    with patch("apps.chat.service.ChatGoogleGenerativeAI.ainvoke", new_callable=AsyncMock) as mock_ainvoke, \
         patch("apps.chat.service.ChatService.search_questions") as mock_search:
        
        mock_ainvoke.return_value = AIMessage(content="Mocked answer based on context.")
        
        # Mock search results to return a sample LangChain document
        from langchain_core.documents import Document
        
        # Mock search results to return a sample LangChain document
        from langchain_core.documents import Document
        mock_search.return_value = [
            (Document(page_content="pH of neutral solution is 7", metadata={"subject": "Chemistry"}), 0.9)
        ]
        
        message = "What is the pH of a neutral solution?"
        
        try:
            response = client.post("/api/v1/chat", json={"message": message})
            print("Response status:", response.status_code)
            print("Response body:", response.json())
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert len(data["sources"]) > 0
            assert data["answer"] == "Mocked answer based on context."
            print("Chat API verification successful!")
            
        except Exception as e:
            print(f"Chat API verification failed with error: {e}")
            raise e

if __name__ == "__main__":
    test_chat_endpoint_logic()
