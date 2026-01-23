import uuid
import json
import pickle
from datetime import datetime
from typing import List, Optional, Tuple
from PyPDF2 import PdfReader
import frontmatter
from sentence_transformers import SentenceTransformer
from core.settings import settings
from core.redis import get_redis_client
from apps.documents.schemas import DocumentMetadata, DocumentStatus, DocumentType, DocumentChunk
import logging

logger = logging.getLogger(__name__)

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def extract_text_from_pdf(file_content: bytes) -> str:
    try:
        import io
        pdf_reader = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_markdown(file_content: bytes) -> str:
    try:
        content = file_content.decode("utf-8")
        post = frontmatter.loads(content)
        text = post.content
        if post.metadata:
            text = f"{json.dumps(post.metadata)}\n{text}"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from Markdown: {e}")
        raise ValueError(f"Failed to extract text from Markdown: {str(e)}")


def extract_text_from_text(file_content: bytes) -> str:
    try:
        return file_content.decode("utf-8").strip()
    except Exception as e:
        logger.error(f"Error extracting text from file: {e}")
        raise ValueError(f"Failed to extract text: {str(e)}")


def extract_text(file_content: bytes, file_type: DocumentType) -> str:
    extractors = {
        DocumentType.PDF: extract_text_from_pdf,
        DocumentType.TEXT: extract_text_from_text,
        DocumentType.MARKDOWN: extract_text_from_markdown,
    }
    extractor = extractors.get(file_type)
    if not extractor:
        raise ValueError(f"Unsupported file type: {file_type}")
    return extractor(file_content)


def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap
    
    return [chunk for chunk in chunks if chunk.strip()]


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def validate_file_size(file_size: int) -> bool:
    max_size = settings.max_file_size_bytes
    return file_size <= max_size


def validate_file_type(filename: str) -> Tuple[bool, Optional[DocumentType]]:
    allowed_types = settings.allowed_file_types
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if extension not in allowed_types:
        return False, None
    
    type_mapping = {
        "pdf": DocumentType.PDF,
        "txt": DocumentType.TEXT,
        "md": DocumentType.MARKDOWN,
    }
    
    return True, type_mapping.get(extension)


class DocumentService:
    def __init__(self):
        self.redis = get_redis_client()
    
    def generate_document_id(self) -> str:
        return f"doc_{uuid.uuid4().hex[:16]}"
    
    async def create_document_metadata(
        self,
        user_id: str,
        filename: str,
        file_type: DocumentType,
        file_size: int,
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> DocumentMetadata:
        doc_id = self.generate_document_id()
        now = datetime.utcnow()
        
        metadata = DocumentMetadata(
            id=doc_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            chunks_count=0,
            status=DocumentStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        doc_key = f"doc:{doc_id}"
        doc_data = {
            "id": doc_id,
            "user_id": user_id,
            "filename": filename,
            "file_type": file_type.value,
            "file_size": file_size,
            "chunks_count": 0,
            "status": DocumentStatus.PENDING.value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "error_message": None
        }
        
        self.redis.hset(doc_key, mapping=doc_data)
        self.redis.sadd(f"user:{user_id}:documents", doc_id)
        
        return metadata
    
    async def update_document_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunks_count: int = None,
        error_message: str = None
    ):
        doc_key = f"doc:{doc_id}"
        updates = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if chunks_count is not None:
            updates["chunks_count"] = chunks_count
        
        if error_message:
            updates["error_message"] = error_message
        
        self.redis.hset(doc_key, mapping=updates)
    
    async def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        doc_key = f"doc:{doc_id}"
        data = self.redis.hgetall(doc_key)
        
        if not data:
            return None
        
        return DocumentMetadata(
            id=data["id"],
            user_id=data["user_id"],
            filename=data["filename"],
            file_type=DocumentType(data["file_type"]),
            file_size=int(data["file_size"]),
            chunks_count=int(data["chunks_count"]),
            status=DocumentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            error_message=data.get("error_message")
        )
    
    async def get_user_documents(self, user_id: str) -> List[DocumentMetadata]:
        doc_ids = self.redis.smembers(f"user:{user_id}:documents")
        documents = []
        
        for doc_id in doc_ids:
            doc = await self.get_document(doc_id)
            if doc:
                documents.append(doc)
        
        return sorted(documents, key=lambda x: x.created_at, reverse=True)
    
    async def save_chunks(self, doc_id: str, chunks: List[str], embeddings: List[List[float]]):
        chunk_key_prefix = f"doc:{doc_id}:chunk"
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_data = {
                "document_id": doc_id,
                "chunk_index": i,
                "content": chunk,
                "embedding": pickle.dumps(embedding).hex()
            }
            
            chunk_key = f"{chunk_key_prefix}:{i}"
            self.redis.hset(chunk_key, mapping=chunk_data)
        
        self.redis.set(f"doc:{doc_id}:chunk_count", len(chunks))
    
    async def get_document_chunks(self, doc_id: str) -> List[DocumentChunk]:
        chunk_count = self.redis.get(f"doc:{doc_id}:chunk_count")
        if not chunk_count:
            return []
        
        chunk_count = int(chunk_count)
        chunks = []
        
        for i in range(chunk_count):
            chunk_key = f"doc:{doc_id}:chunk:{i}"
            data = self.redis.hgetall(chunk_key)
            
            if data:
                embedding = None
                if data.get("embedding"):
                    embedding = pickle.loads(bytes.fromhex(data["embedding"]))
                
                chunks.append(DocumentChunk(
                    document_id=doc_id,
                    chunk_index=int(data["chunk_index"]),
                    content=data["content"],
                    embedding=embedding
                ))
        
        return chunks
    
    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        doc_key = f"doc:{doc_id}"
        
        if not self.redis.exists(doc_key):
            return False
        
        chunk_count = self.redis.get(f"doc:{doc_id}:chunk_count")
        if chunk_count:
            for i in range(int(chunk_count)):
                self.redis.delete(f"doc:{doc_id}:chunk:{i}")
        
        self.redis.delete(doc_key)
        self.redis.delete(f"doc:{doc_id}:chunk_count")
        self.redis.srem(f"user:{user_id}:documents", doc_id)
        
        return True


document_service = DocumentService()
