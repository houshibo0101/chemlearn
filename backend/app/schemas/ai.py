"""
AI 问答相关 Schema
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # user / assistant
    content: str


class AIChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    context: Optional[str] = Field(None, description="附加上下文，如题目内容")


class AIChatResponse(BaseModel):
    reply: str
    model: str


class WrongQuestionAIRequest(BaseModel):
    wrong_question_id: int
    follow_up: Optional[str] = Field(None, description="追问内容，为空则首次讲解")
