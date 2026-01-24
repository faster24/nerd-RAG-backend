from typing import List, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_mongodb import MongoDBAtlasVectorSearch
from core.settings import settings
from apps.documents.service import get_embeddings
from apps.chat.schemas import ChatSource
import logging

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.embeddings = get_embeddings()
        
        from pymongo import MongoClient
        client = MongoClient(settings.mongodb_uri)
        db = client[settings.mongodb_db_name]
        self.questions_collection = db["questions"]
        
        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.questions_collection,
            embedding=self.embeddings,
            index_name=settings.mongodb_vector_index_name,
            relevance_score_fn="cosine",
            text_key="search_text",
            embedding_key="embedding",
        )
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            if not settings.google_api_key:
                logger.warning("GOOGLE_API_KEY not found in settings. Gemini LLM will not be functional.")
            self._llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.google_api_key,
                temperature=0.7,
            )
        return self._llm

    async def search_questions(self, query: str, k: int = 5) -> List[Tuple[dict, float]]:
        """Search the questions collection using vector search."""
        # Using similarity_search_with_score
        # We wrap in a thread pool if it's blocking, but usually LangChain's 
        # MongoDBAtlasVectorSearch is not natively async for search.
        # However, for simplicity here we just call it.
        # In a real app we might use run_in_executor
        results = self.vector_store.similarity_search_with_score(query, k=k)
        return results

    async def get_chat_response(self, message: str, history: List[dict] = None) -> Tuple[str, List[ChatSource]]:
        """Generate a response using Gemini based on retrieved context."""
        # 1. Search for context
        search_results = await self.search_questions(message)
        
        context_parts = []
        sources = []
        
        for doc, score in search_results:
            content = doc.page_content
            meta = doc.metadata
            
            # Since we inserted them as dicts in add_questions, 
            # and similarity_search returns LangChain Documents,
            # page_content will be 'search_text' (or whatever LangChain uses)
            # Actually, LangChain's MongoDBAtlasVectorSearch usually expects 'text' field by default
            # but in our re_embed script we just updated 'embedding'.
            # and in add_questions we used insert_many.
            
            # Let's check how LangChain handles the mapping.
            # By default it looks for 'text' field.
            
            context_parts.append(content)
            sources.append(ChatSource(
                subject=meta.get("subject", "Unknown"),
                topic_path=meta.get("topic_path", []),
                content=content[:200] + "..." # Snippet
            ))

        context_str = "\n\n".join(context_parts)
        
        # 2. Build Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant for a learning platform. Use the following pieces of context to answer the user's question. If you don't know the answer, just say that you don't know, don't try to make up an answer.\n\nContext: {context}"),
            ("human", "{question}"),
        ])
        
        # 3. Chain and Invoke
        chain = prompt | self.llm
        response = await chain.ainvoke({"context": context_str, "question": message})
        
        return response.content, sources

chat_service = ChatService()
