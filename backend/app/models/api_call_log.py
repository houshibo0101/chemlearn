"""
API 调用日志模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Index
from app.core.database import Base


class APICallLog(Base):
    __tablename__ = "api_call_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    username = Column(String(64), index=True, nullable=True)
    endpoint = Column(String(256), nullable=False, comment="调用的接口路径")
    method = Column(String(16), nullable=False, comment="HTTP方法")
    ip = Column(String(64), nullable=True, comment="客户端IP")
    api_key = Column(String(128), nullable=True, comment="使用的API Key")
    status_code = Column(Integer, nullable=True, comment="响应状态码")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index('idx_api_call_user_time', 'user_id', 'created_at'),
    )
