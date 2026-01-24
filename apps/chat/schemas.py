from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = None


class ChatSource(BaseModel):
    subject: str
    topic_path: List[str]
    content: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]
