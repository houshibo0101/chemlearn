"""
API 开放平台 - API Key 模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, comment="密钥名称/用途")
    key = Column(String(128), unique=True, index=True, nullable=False, comment="API Key")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scope = Column(String(256), default="all", comment="权限范围：question/wrong/ai/all，多个用逗号分隔")
    is_active = Column(Boolean, default=True)
    call_count = Column(Integer, default=0, comment="总调用次数")
    daily_limit = Column(Integer, default=1000, comment="每日调用限额，0表示不限")
    rate_limit_per_minute = Column(Integer, default=60, comment="每分钟调用限额，0表示不限")
    daily_call_count = Column(Integer, default=0, comment="今日调用次数")
    last_call_date = Column(String(10), nullable=True, comment="最后调用日期 YYYY-MM-DD")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
