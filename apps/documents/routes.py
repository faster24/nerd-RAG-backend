from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from apps.documents.service import document_service
from apps.documents.service import validate_file_size, validate_file_type, extract_text, chunk_text, embed_texts
from apps.documents.schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentChunksResponse,
    DocumentChunk,
    BatchUploadResponse,
    UploadError,
    HealthCheckResponse,
    DocumentType,
    DocumentStatus,
)
from core.middleware import verify_firebase_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


class ChunkingConfig(BaseModel):
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 50


async def process_document(
    user_id: str,
    file: UploadFile,
    config: Optional[ChunkingConfig] = None
) -> DocumentResponse:
    file_content = await file.read()
    file_size = len(file_content)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    is_valid_size = validate_file_size(file_size)
    if not is_valid_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed size of 50MB"
        )

    is_valid_type, file_type = validate_file_type(file.filename)
    if not is_valid_type or not file_type:
        allowed_types = ["pdf", "text", "md"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )

    chunk_size = config.chunk_size if config and config.chunk_size else 500
    chunk_overlap = config.chunk_overlap if config and config.chunk_overlap else 50

    metadata = await document_service.create_document_metadata(
        user_id=user_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    try:
        await document_service.update_document_status(
            metadata.id,
            DocumentStatus.PROCESSING
        )
        
        text = extract_text(file_content, file_type)
        
        chunks = chunk_text(
            text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if chunks:
            embeddings = embed_texts(chunks)
            await document_service.save_chunks(metadata.id, chunks, embeddings)
        else:
            embeddings = []
        
        await document_service.update_document_status(
            metadata.id,
            DocumentStatus.COMPLETED,
            chunks_count=len(chunks)
        )
        
        final_metadata = await document_service.get_document(metadata.id)
        
        if final_metadata is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve document metadata after processing"
            )
        
        return DocumentResponse(
            id=metadata.id,
            message="Document uploaded and processed successfully",
            document=final_metadata
        )
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await document_service.update_document_status(
            metadata.id,
            DocumentStatus.FAILED,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    summary="Upload a document",
    description="Upload a PDF, text, or markdown file. The document will be processed, chunked, and embedded."
)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    user_data: dict = Depends(verify_firebase_token)
):
    user_id = user_data["uid"]
    
    config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    return await process_document(user_id, file, config)


@router.post(
    "/upload/batch",
    response_model=BatchUploadResponse,
    summary="Upload multiple documents",
    description="Upload multiple PDF, text, or markdown files at once."
)
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    chunk_size: int = Form(500),
    chunk_overlap: int = Form(50),
    user_data: dict = Depends(verify_firebase_token)
):
    user_id = user_data["uid"]
    config = ChunkingConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    successful = []
    failed = []
    
    for file in files:
        try:
            result = await process_document(user_id, file, config)
            successful.append(result)
        except HTTPException as e:
            failed.append(UploadError(filename=file.filename or "unknown", error=e.detail))
        except Exception as e:
            failed.append(UploadError(filename=file.filename or "unknown", error=str(e)))
    
    return BatchUploadResponse(successful=successful, failed=failed)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List user documents",
    description="Get a list of all documents uploaded by the current user."
)
async def list_documents(
    user_data: dict = Depends(verify_firebase_token)
):
    user_id = user_data["uid"]
    documents = await document_service.get_user_documents(user_id)
    return DocumentListResponse(documents=documents, total=len(documents))


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
    description="Get metadata for a specific document."
)
async def get_document(
    document_id: str,
    user_data: dict = Depends(verify_firebase_token)
):
    user_id = user_data["uid"]
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )
    
    return DocumentResponse(
        id=document.id,
        message="Document retrieved successfully",
        document=document
    )


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunksResponse,
    summary="Get document chunks",
    description="Get all chunks and embeddings for a specific document."
)
async def get_document_chunks(
    document_id: str,
    user_data: dict = Depends(verify_firebase_token)
):
    user_id = user_data["uid"]
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )
    
    chunks = await document_service.get_document_chunks(document_id)
    
    return DocumentChunksResponse(
        document_id=document_id,
        chunks=chunks,
        total=len(chunks)
    )


@router.delete(
    "/{document_id}",
    summary="Delete a document",
    description="Delete a document and all its chunks from the system."
)
async def delete_document(
    document_id: str,
    user_data: dict = Depends(verify_firebase_token)
):
    user_id = user_data["uid"]
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    if document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this document"
        )
    
    success = await document_service.delete_document(document_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )
    
    return {"message": "Document deleted successfully"}


@router.get(
    "/health/check",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check if Redis and embedding model are available."
)
async def health_check():
    from core.redis import check_redis_connection
    
    redis_connected = check_redis_connection()
    
    embedding_model_loaded = False
    try:
        from apps.documents.service import get_embedding_model
        get_embedding_model()
        embedding_model_loaded = True
    except Exception:
        embedding_model_loaded = False
    
    return HealthCheckResponse(
        redis_connected=redis_connected,
        embedding_model_loaded=embedding_model_loaded
    )
