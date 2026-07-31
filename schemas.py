from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str


class ChatResponseData(BaseModel):
    reply: str
    session_id: str
    retrieved_topics: list[str]
    llm_used: str
    message_id: int


class ChatResponse(BaseModel):
    success: bool
    data: Optional[ChatResponseData] = None
    error: Optional[dict] = None


class SessionInfo(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int


class SessionsListResponse(BaseModel):
    success: bool
    data: Optional[list[SessionInfo]] = None
    error: Optional[dict] = None


class CreateSessionRequest(BaseModel):
    session_id: str


class CreateSessionResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None


class MessageInfo(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class HistoryResponseData(BaseModel):
    session_id: str
    title: Optional[str]
    messages: list[MessageInfo]


class HistoryResponse(BaseModel):
    success: bool
    data: Optional[HistoryResponseData] = None
    error: Optional[dict] = None


class DeleteSessionResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None


class ArticleInfo(BaseModel):
    id: int
    topic: str
    question: str
    answer: str


class KnowledgeResponse(BaseModel):
    success: bool
    data: Optional[list[ArticleInfo]] = None
    error: Optional[dict] = None