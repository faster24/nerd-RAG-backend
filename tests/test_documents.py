import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import io
from manage import app
from apps.documents.service import (
    validate_file_size,
    validate_file_type,
    extract_text_from_text,
    extract_text_from_pdf,
    extract_text_from_markdown,
    chunk_text,
    embed_texts,
    DocumentService,
)
from apps.documents.schemas import DocumentType, DocumentStatus, DocumentMetadata
from core.middleware import verify_firebase_token
import numpy as np


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth_dependency():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test_user"}
    yield
    app.dependency_overrides = {}


class TestFileValidation:
    def test_validate_file_size_valid(self):
        assert validate_file_size(1024 * 1024) == True  # 1MB

    def test_validate_file_size_too_large(self):
        assert validate_file_size(60 * 1024 * 1024) == False  # 60MB

    def test_validate_file_type_valid_pdf(self):
        valid, file_type = validate_file_type("test.pdf")
        assert valid == True
        assert file_type == DocumentType.PDF

    def test_validate_file_type_valid_text(self):
        valid, file_type = validate_file_type("test.txt")
        assert valid == True
        assert file_type == DocumentType.TEXT

    def test_validate_file_type_valid_markdown(self):
        valid, file_type = validate_file_type("test.md")
        assert valid == True
        assert file_type == DocumentType.MARKDOWN

    def test_validate_file_type_invalid(self):
        valid, file_type = validate_file_type("test.docx")
        assert valid == False
        assert file_type is None

    def test_validate_file_type_no_extension(self):
        valid, file_type = validate_file_type("test")
        assert valid == False
        assert file_type is None


class TestTextExtraction:
    def test_extract_text_from_text(self):
        content = b"Hello World\nThis is a test."
        result = extract_text_from_text(content)
        assert result == "Hello World\nThis is a test."

    def test_extract_text_from_markdown(self):
        content = b"# Title\n\nThis is content.\n\n---\n\nMore content."
        result = extract_text_from_markdown(content)
        assert result == "# Title\n\nThis is content.\n\n---\n\nMore content."

    def test_extract_text_from_markdown_with_frontmatter(self):
        content = b"""---
title: Test Document
author: John Doe
---

# Main Content

This is the body text.
"""
        result = extract_text_from_markdown(content)
        assert "# Main Content" in result
        assert "This is the body text." in result

    @patch('apps.documents.service.PdfReader')
    def test_extract_text_from_pdf(self, mock_pdf_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PDF Content Page 1"
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        content = b"fake pdf content"
        result = extract_text_from_pdf(content)
        assert result == "PDF Content Page 1"


class TestTextChunking:
    def test_chunk_text_small_text(self):
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        assert chunks == ["This is a short text."]

    def test_chunk_text_large_text(self):
        text = "A" * 600  # Text longer than chunk_size
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) > 1
        assert len(chunks[0]) == 500
        assert len(chunks[1]) == 150  # 500 - 50 + remaining

    def test_chunk_text_with_overlap(self):
        text = "A" * 600
        chunks = chunk_text(text, chunk_size=300, chunk_overlap=100)
        assert len(chunks) >= 2
        # Check that overlap works - last 100 chars of first chunk should match first 100 of second
        assert chunks[0][-100:] == chunks[1][:100]

    def test_chunk_text_empty(self):
        chunks = chunk_text("", chunk_size=500, chunk_overlap=50)
        assert chunks == []

    def test_chunk_text_only_whitespace(self):
        chunks = chunk_text("   \n\t   ", chunk_size=500, chunk_overlap=50)
        assert chunks == []


class TestEmbedding:
    @patch('apps.documents.service.SentenceTransformer')
    def test_embed_texts(self, mock_transformer):
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_transformer.return_value = mock_model

        texts = ["Text 1", "Text 2"]
        embeddings = embed_texts(texts)

        assert embeddings == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_model.encode.assert_called_once()

    @patch('apps.documents.service.SentenceTransformer')
    def test_embed_texts_empty(self, mock_transformer):
        texts = []
        embeddings = embed_texts(texts)
        assert embeddings == []


class TestDocumentService:
    @patch('apps.documents.service.get_redis_client')
    def test_create_document_metadata(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        service = DocumentService()

        import asyncio
        async def run_test():
            metadata = await service.create_document_metadata(
                user_id="user123",
                filename="test.pdf",
                file_type=DocumentType.PDF,
                file_size=1024
            )

            assert metadata.id.startswith("doc_")
            assert metadata.user_id == "user123"
            assert metadata.filename == "test.pdf"
            assert metadata.file_type == DocumentType.PDF
            assert metadata.file_size == 1024
            assert metadata.status == DocumentStatus.PENDING

            # Verify Redis calls
            mock_redis.hset.assert_called_once()
            mock_redis.sadd.assert_called_once()

        asyncio.run(run_test())

    @patch('apps.documents.service.get_redis_client')
    def test_get_document(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            "id": "doc_123",
            "user_id": "user123",
            "filename": "test.pdf",
            "file_type": "pdf",
            "file_size": "1024",
            "chunks_count": "5",
            "status": "completed",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        mock_get_redis.return_value = mock_redis

        service = DocumentService()

        import asyncio
        async def run_test():
            doc = await service.get_document("doc_123")
            assert doc is not None
            assert doc.id == "doc_123"
            assert doc.filename == "test.pdf"
            assert doc.status == DocumentStatus.COMPLETED

        asyncio.run(run_test())

    @patch('apps.documents.service.get_redis_client')
    def test_get_document_not_found(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        mock_get_redis.return_value = mock_redis

        service = DocumentService()

        import asyncio
        async def run_test():
            doc = await service.get_document("doc_123")
            assert doc is None

        asyncio.run(run_test())


class TestAPIEndpoints:
    def test_upload_document_missing_filename(self):

        # Create a file-like object without filename
        file_content = b"Hello World"
        file_like = io.BytesIO(file_content)
        file_like.name = None  # No filename

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("", file_like, "text/plain")},
            data={"chunk_size": 500, "chunk_overlap": 50}
        )

        assert response.status_code in [400, 422]
        if response.status_code == 400:
             assert "Filename is required" in response.json()["detail"]

    @patch('apps.documents.service.DocumentService.create_document_metadata')
    @patch('apps.documents.service.DocumentService.update_document_status')
    @patch('apps.documents.service.DocumentService.get_document')
    @patch('apps.documents.service.extract_text')
    @patch('apps.documents.service.chunk_text')
    @patch('apps.documents.service.embed_texts')
    @patch('apps.documents.service.DocumentService.save_chunks')
    def test_upload_document_success(self, mock_save_chunks, mock_embed, mock_chunk,
                                   mock_extract, mock_get_doc, mock_update_status,
                                   mock_create_metadata):

        # Mock successful document processing
        from datetime import datetime
        mock_metadata = DocumentMetadata(
            id="doc_123",
            user_id="test_user",
            filename="test.txt",
            file_type=DocumentType.TEXT,
            file_size=11,
            chunks_count=0,
            status=DocumentStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_create_metadata.return_value = mock_metadata

        mock_extract.return_value = "Extracted text content"
        mock_chunk.return_value = ["Chunk 1", "Chunk 2"]
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        mock_final_doc = mock_metadata.model_copy(update={"status": DocumentStatus.COMPLETED, "chunks_count": 2})
        mock_get_doc.return_value = mock_final_doc

        file_content = b"Hello World"
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
            data={"chunk_size": 500, "chunk_overlap": 50}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "doc_123"
        assert "successfully" in data["message"]

    def test_upload_document_invalid_file_type(self):

        file_content = b"Fake DOCX content"
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"chunk_size": 500, "chunk_overlap": 50}
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_upload_document_file_too_large(self):

        # Create a file larger than 50MB
        large_content = b"X" * (60 * 1024 * 1024)  # 60MB
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")},
            data={"chunk_size": 500, "chunk_overlap": 50}
        )

        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]

    @patch('apps.documents.service.DocumentService.get_user_documents')
    def test_list_documents(self, mock_get_user_docs):
        # Create a valid DocumentMetadata object instead of MagicMock
        from datetime import datetime
        doc = DocumentMetadata(
            id="doc_123",
            user_id="test_user",
            filename="test.txt",
            file_type=DocumentType.TEXT,
            file_size=100,
            chunks_count=1,
            status=DocumentStatus.COMPLETED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        mock_get_user_docs.return_value = [doc]

        response = client.get("/api/v1/documents")

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data

    @patch('apps.documents.service.DocumentService.get_document')
    def test_get_document_not_found(self, mock_get_doc):
        mock_get_doc.return_value = None

        response = client.get("/api/v1/documents/doc_123")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('apps.documents.service.DocumentService.get_document')
    def test_get_document_access_denied(self, mock_get_doc):

        mock_doc = MagicMock()
        mock_doc.user_id = "other_user"
        mock_get_doc.return_value = mock_doc

        response = client.get("/api/v1/documents/doc_123")

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @patch('apps.documents.service.DocumentService.get_document')
    @patch('apps.documents.service.DocumentService.delete_document')
    def test_delete_document_success(self, mock_delete, mock_get_doc):

        mock_doc = MagicMock()
        mock_doc.user_id = "test_user"
        mock_get_doc.return_value = mock_doc
        mock_delete.return_value = True

        response = client.delete("/api/v1/documents/doc_123")

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    @patch('core.redis.check_redis_connection')
    def test_health_check(self, mock_redis_check):
        mock_redis_check.return_value = True

        response = client.get("/api/v1/documents/health/check")

        assert response.status_code == 200
        data = response.json()
        assert data["redis_connected"] == True
        assert "embedding_model_loaded" in data