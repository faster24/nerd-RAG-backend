from fastapi import APIRouter, HTTPException
from apps.chat.schemas import ChatRequest, ChatResponse
from apps.chat.service import chat_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        answer, sources = await chat_service.get_chat_response(request.message, request.history)
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))
