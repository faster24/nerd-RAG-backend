import sys
import os
from pathlib import Path

# Mock settings or just use defaults
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from sentence_transformers import SentenceTransformer
    print(f"Testing embedding model: {EMBEDDING_MODEL}")
    
    test_texts = ["Hello world", "This is a test of the embedding system."]
    
    print("\n1. Testing SentenceTransformer directly...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(test_texts)
    print(f"✅ Successfully generated {len(embeddings)} embeddings.")
    print(f"   Dimension: {len(embeddings[0])}")

    print("\n2. Testing LangChain HuggingFaceEmbeddings...")
    hf_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    embeddings = hf_embeddings.embed_documents(test_texts)
    print(f"✅ Successfully generated {len(embeddings)} embeddings.")
    print(f"   Dimension: {len(embeddings[0])}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
