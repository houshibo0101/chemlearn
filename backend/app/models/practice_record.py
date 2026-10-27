# -*- coding: utf-8 -*-
"""
做题记录模型
- 每次提交答案（无论对错）都写入一条记录，作为学习报告与做题历史的数据源
- source 区分来源：practice（刷题）/ assignment（作业）/ exam（考试）
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Index
from app.core.database import Base


class PracticeRecord(Base):
    __tablename__ = "practice_records"
    __table_args__ = (
        Index("ix_practice_records_user_time", "user_id", "submitted_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    source = Column(String(16), default="practice", nullable=False, comment="来源: practice/assignment/exam")
    user_answer = Column(Text, nullable=True, comment="用户答案")
    is_correct = Column(Boolean, default=False, nullable=False, comment="是否正确")
    score = Column(Integer, nullable=True, comment="得分（客观题 1/0，主观题按关键词）")
    total_score = Column(Integer, nullable=True, comment="该题满分")
    time_spent = Column(Integer, nullable=True, comment="用时（秒）")
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="提交时间(UTC)")
