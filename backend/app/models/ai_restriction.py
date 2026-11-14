"""AI 问答使用限制：无关问题计数与停用状态"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from app.core.database import Base


class AIRestriction(Base):
    __tablename__ = "ai_restrictions"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    offtopic_count = Column(Integer, default=0, nullable=False, comment="累计无关提问次数")
    banned = Column(Boolean, default=False, nullable=False, comment="是否停用 AI 问答")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
