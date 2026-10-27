"""
题目相关 Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    title: str = Field(..., max_length=512)
    content: Optional[str] = None
    question_type: str = Field("single", description="single/multiple/fill/calculation")
    difficulty: str = Field("medium", description="easy/medium/hard")
    grade: Optional[str] = None
    knowledge_point: Optional[str] = None
    options: Optional[str] = Field(None, description="选项JSON字符串")
    answer: str
    analysis: Optional[str] = None


class QuestionUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    grade: Optional[str] = None
    knowledge_point: Optional[str] = None
    options: Optional[str] = None
    answer: Optional[str] = None
    analysis: Optional[str] = None


class QuestionOut(BaseModel):
    id: int
    question_code: Optional[str] = None
    title: str
    content: Optional[str] = None
    question_type: str
    difficulty: str
    grade: Optional[str] = None
    knowledge_point: Optional[str] = None
    options: Optional[str] = None
    answer: Optional[str] = None
    analysis: Optional[str] = None
    images: Optional[str] = None
    keywords: Optional[str] = None
    source: Optional[str] = None
    sub_questions: Optional[str] = None
    creator_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionPracticeOut(BaseModel):
    """刷题时返回（不含答案）"""
    id: int
    question_code: Optional[str] = None
    title: str
    content: Optional[str] = None
    question_type: str
    difficulty: str
    grade: Optional[str] = None
    knowledge_point: Optional[str] = None
    options: Optional[str] = None
    images: Optional[str] = None
    source: Optional[str] = None
    sub_questions: Optional[str] = None

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    question_id: int
    user_answer: str
    time_spent: Optional[int] = None   # 用时（秒），可选
    source: Optional[str] = "practice"  # 来源：practice/assignment/exam


class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    correct_answer: str
    user_answer: Optional[str] = None
    analysis: Optional[str] = None
    recorded_as_wrong: bool = False
    score: Optional[float] = None
    ai_comment: Optional[str] = None
    sub_results: Optional[list] = None
