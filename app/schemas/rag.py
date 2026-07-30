from pydantic import BaseModel, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str = Field(..., example="user", description="'user' or 'assistant'")
    content: str = Field(..., example="What is the flight policy?")


class Citation(BaseModel):
    document_name: str
    section_title: str
    excerpt: str
    relevance_score: float


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, example="What is the daily meal allowance limit?")
    document_filter: Optional[str] = Field(default=None, example="Expense Policy", description="Filter search to specific policy document")
    history: Optional[List[ChatMessage]] = Field(default=None, description="Previous conversation turns for context")


class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    grounded: bool
    query: str
