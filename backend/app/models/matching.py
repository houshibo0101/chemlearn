# -*- coding: utf-8 -*-
"""化学连连看：题集、配对项、作答记录

一套「关卡」= 若干配对（左项 ↔ 右项），玩家在打乱的卡片里把同一对的两张点掉。
内容覆盖物质名称、官能团、化学方程式、俗名俗称等，类别由 MatchingSet.category 标记。
"""
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text)
from sqlalchemy.orm import relationship

from app.core.database import Base

# 类别取值 -> 中文名，前端/接口返回时统一用中文标签
CATEGORY_LABELS = {
    "substance": "物质名称",
    "functional_group": "官能团",
    "equation": "化学方程式",
    "common_name": "俗名俗称",
    "mixed": "综合",
}

DIFFICULTY_LABELS = {
    "easy": "简单",
    "medium": "中等",
    "hard": "较难",
}


def _now():
    return datetime.now(timezone.utc)


class MatchingSet(Base):
    __tablename__ = "matching_sets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(80), nullable=False)
    description = Column(String(500), nullable=True)
    category = Column(String(32), default="mixed", nullable=False, index=True)
    difficulty = Column(String(16), default="medium", nullable=False)
    grade = Column(String(32), nullable=True, comment="适用学段，如高一")
    is_active = Column(Boolean, default=True, nullable=False, comment="停用后学生看不到")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    play_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    pairs = relationship(
        "MatchingPair", back_populates="set", cascade="all, delete-orphan",
        order_by="MatchingPair.order_index", lazy="selectin",
    )
    creator = relationship("User", foreign_keys=[creator_id], lazy="joined")


class MatchingPair(Base):
    __tablename__ = "matching_pairs"

    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(Integer, ForeignKey("matching_sets.id"), nullable=False, index=True)
    left_text = Column(String(200), nullable=False)
    right_text = Column(String(200), nullable=False)
    hint = Column(Text, nullable=True, comment="配对成功后的讲解/提示")
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)

    set = relationship("MatchingSet", back_populates="pairs")


class MatchingRecord(Base):
    __tablename__ = "matching_records"
    __table_args__ = (
        Index("ix_matching_records_set_score", "set_id", "score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    set_id = Column(Integer, ForeignKey("matching_sets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, default=0, nullable=False)
    mistakes = Column(Integer, default=0, nullable=False)
    pairs_total = Column(Integer, default=0, nullable=False)
    max_combo = Column(Integer, default=0, nullable=False)
    duration_seconds = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False, index=True)

    set = relationship("MatchingSet", lazy="joined")
    user = relationship("User", lazy="joined")
