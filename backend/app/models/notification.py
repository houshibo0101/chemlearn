"""
站内通知模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False, comment="接收者用户ID")
    title = Column(String(256), nullable=False, comment="通知标题")
    content = Column(Text, nullable=True, comment="通知内容")
    ntype = Column(String(32), default="system", comment="类型：assignment/exam/system")
    related_id = Column(Integer, nullable=True, comment="关联业务ID（作业/考试等）")
    is_read = Column(Boolean, default=False, index=True, comment="是否已读")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
