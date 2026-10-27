"""
错题记录模型
- 同一用户同一题目只保留一条记录（去重）
- 记录错误次数和最后一次错误时间
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_user_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    wrong_count = Column(Integer, default=1, nullable=False, comment="错误次数")
    user_answer = Column(Text, nullable=True, comment="用户最后一次错误答案")
    last_wrong_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, comment="最后一次错误时间")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])
    question = relationship("Question", foreign_keys=[question_id])
