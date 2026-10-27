"""
错题相关 Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WrongQuestionOut(BaseModel):
    id: int
    user_id: int
    question_id: int
    wrong_count: int
    user_answer: Optional[str] = None
    last_wrong_at: datetime
    created_at: datetime
    # 关联题目信息
    question_code: Optional[str] = None
    question_title: Optional[str] = None
    question_content: Optional[str] = None
    question_type: Optional[str] = None
    correct_answer: Optional[str] = None
    analysis: Optional[str] = None

    class Config:
        from_attributes = True
