"""
AI 使用量统计模型
- 记录每次 AI 调用的 token 消耗
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class AIUsage(Base):
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    model = Column(String(64), nullable=False, comment="使用的AI模型")
    prompt_tokens = Column(Integer, default=0, comment="输入token数")
    completion_tokens = Column(Integer, default=0, comment="输出token数")
    total_tokens = Column(Integer, default=0, comment="总token数")
    usage_type = Column(String(32), default="chat", comment="chat / wrong_explain")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_ai_usage_user_time", "user_id", "created_at"),
    )
