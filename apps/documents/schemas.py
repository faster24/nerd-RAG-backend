from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "md"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    filename: str
    file_type: DocumentType
    file_size: int
    chunk_size: int = 500
    chunk_overlap: int = 50


class DocumentCreate(DocumentBase):
    pass


class DocumentMetadata(BaseModel):
    id: str
    user_id: str
    filename: str
    file_type: DocumentType
    file_size: int
    chunks_count: int
    status: DocumentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None


class DocumentResponse(BaseModel):
    id: str
    message: str
    document: DocumentMetadata


class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total: int


class DocumentChunk(BaseModel):
    document_id: str
    chunk_index: int
    content: str
    embedding: Optional[List[float]] = None


class DocumentChunksResponse(BaseModel):
    document_id: str
    chunks: List[DocumentChunk]
    total: int


class UploadError(BaseModel):
    filename: str
    error: str


class BatchUploadResponse(BaseModel):
    successful: List[DocumentResponse]
    failed: List[UploadError]


class HealthCheckResponse(BaseModel):
    redis_connected: bool
    mongodb_connected: bool
    embedding_model_loaded: bool
