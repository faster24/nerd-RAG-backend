import uuid
import json
import pickle
from datetime import datetime
from typing import List, Optional, Tuple
from PyPDF2 import PdfReader
import frontmatter
import logging
from core.settings import settings
from core.redis import get_redis_client
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from apps.documents.schemas import DocumentMetadata, DocumentStatus, DocumentType, DocumentChunk
_embeddings = None

logger = logging.getLogger(__name__)

def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        logger.info("Embedding model loaded successfully")
    return _embeddings




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
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)


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
        self.mongo_client = MongoClient(settings.mongodb_uri)
        self.db = self.mongo_client[settings.mongodb_db_name]
        self.collection = self.db[settings.mongodb_collection_name]
        self.embeddings = get_embeddings()
        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.collection,
            embedding=self.embeddings,
            index_name=settings.mongodb_vector_index_name,
            relevance_score_fn="cosine",
        )
    
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
        
        # Store metadata in MongoDB instead of Redis
        self.db.metadata.insert_one(doc_data)
        
        # Keep Redis for quick user document list if needed, but let's migrate to Mongo
        # self.redis.hset(doc_key, mapping=doc_data)
        # self.redis.sadd(f"user:{user_id}:documents", doc_id)
        
        return metadata
    
    async def update_document_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        chunks_count: int = None,
        error_message: str = None
    ):
        updates = {
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if chunks_count is not None:
            updates["chunks_count"] = chunks_count
        
        if error_message:
            updates["error_message"] = error_message
            
        self.db.metadata.update_one(
            {"id": doc_id},
            {"$set": updates}
        )
    
    async def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        data = self.db.metadata.find_one({"id": doc_id})
        
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
        cursor = self.db.metadata.find({"user_id": user_id}).sort("created_at", -1)
        documents = []
        
        for data in cursor:
            documents.append(DocumentMetadata(
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
            ))
        
        return documents
    
    async def save_chunks(self, doc_id: str, chunks: List[str], embeddings: List[List[float]]):
        # We use LangChain's vector_store to save chunks
        # LangChain's MongoDBAtlasVectorSearch handles embedding if we don't provide it, 
        # but here we already have embeddings if we want to use them.
        # Actually, MongoDBAtlasVectorSearch.add_texts will use the internal embedding function.
        
        documents = [
            Document(
                page_content=chunk,
                metadata={"document_id": doc_id, "chunk_index": i}
            )
            for i, chunk in enumerate(chunks)
        ]
        
        self.vector_store.add_documents(documents)
    
    async def get_document_chunks(self, doc_id: str) -> List[DocumentChunk]:
        # Retrieve chunks from MongoDB collection
        cursor = self.collection.find({"metadata.document_id": doc_id}).sort("metadata.chunk_index", 1)
        chunks = []
        
        for data in cursor:
            chunks.append(DocumentChunk(
                document_id=doc_id,
                chunk_index=data["metadata"]["chunk_index"],
                content=data["text"],
                embedding=data.get("embedding") # Note: Atlas Search might not return vector by default
            ))
        
        return chunks
    
    async def delete_document(self, doc_id: str, user_id: str) -> bool:
        # Delete metadata
        res = self.db.metadata.delete_one({"id": doc_id, "user_id": user_id})
        if res.deleted_count == 0:
            return False
        
        # Delete chunks from vector collection
        self.collection.delete_many({"metadata.document_id": doc_id})
        
        return True


document_service = DocumentService()
