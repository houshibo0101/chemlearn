# -*- coding: utf-8 -*-
"""
后台 AI 任务

AI 讲解、AI 变式题都要等模型几十秒，前端同步等着体验很差。
改成：接口立即返回任务 id，后台协程执行，完成后写通知，用户从通知中心/轮询拿结果。
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, Boolean

from app.core.database import Base


class AITask(Base):
    __tablename__ = "ai_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    task_type = Column(String(20), nullable=False, comment="explain=错题讲解 / variant=变式题")
    status = Column(String(16), default="pending", nullable=False, comment="pending/running/done/failed")
    ref_id = Column(Integer, nullable=True, comment="关联 id：错题记录 id")
    payload = Column(JSON, nullable=True, comment="输入参数，如 {follow_up, count}")
    result = Column(JSON, nullable=True, comment="生成结果")
    error = Column(Text, nullable=True)

    notified = Column(Boolean, default=False, comment="是否已发通知")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
