import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_huggingface import HuggingFaceEmbeddings
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def re_embed_questions():
    load_dotenv()
    
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "rag_system")
    embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    
    if not mongodb_uri:
        logger.error("MONGODB_URI not found in .env")
        sys.exit(1)
        
    logger.info(f"Connecting to MongoDB: {mongodb_db_name}")
    client = MongoClient(mongodb_uri)
    db = client[mongodb_db_name]
    collection = db["questions"]
    
    logger.info(f"Loading embedding model: {embedding_model_name}")
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
    
    cursor = collection.find({})
    total_docs = collection.count_documents({})
    logger.info(f"Found {total_docs} documents to process")
    
    count = 0
    for doc in cursor:
        doc_id = doc["_id"]
        search_text = doc.get("search_text")
        
        if not search_text:
            logger.warning(f"Document {doc_id} has no search_text. Skipping.")
            continue
            
        # Generate new embedding
        new_embedding = embeddings.embed_query(search_text)
        
        # Update document
        collection.update_one(
            {"_id": doc_id},
            {"$set": {"embedding": new_embedding}}
        )
        
        count += 1
        if count % 10 == 0 or count == total_docs:
            logger.info(f"Processed {count}/{total_docs} documents")
            
    logger.info("Re-embedding completed successfully")
    client.close()

if __name__ == "__main__":
    re_embed_questions()
