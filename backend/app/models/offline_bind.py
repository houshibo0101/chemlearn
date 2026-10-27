"""
离线账户绑定模型
- 记录正常账户和离线账户的绑定关系
- 每个正常账户最多绑定2个离线账户
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class OfflineBind(Base):
    __tablename__ = "offline_binds"
    __table_args__ = (
        UniqueConstraint("parent_user_id", "offline_user_id", name="uq_parent_offline"),
    )

    id = Column(Integer, primary_key=True, index=True)
    parent_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="正常账户ID")
    offline_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="离线账户ID")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    parent_user = relationship("User", foreign_keys=[parent_user_id])
    offline_user = relationship("User", foreign_keys=[offline_user_id])
