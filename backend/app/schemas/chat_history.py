"""
对话历史相关 Schema
"""
from datetime import datetime
from pydantic import BaseModel


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryClear(BaseModel):
    message: str = "对话历史已清空"
