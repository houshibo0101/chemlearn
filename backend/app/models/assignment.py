"""
作业模型
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum
from app.core.database import Base


class AssignmentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), nullable=False, comment="作业标题")
    description = Column(Text, nullable=True, comment="作业说明")
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_ids = Column(JSON, default=list, comment="题目ID列表")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="截止时间")
    status = Column(Enum(AssignmentStatus), default=AssignmentStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AssignmentClass(Base):
    __tablename__ = "assignment_classes"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, default=dict, comment="学生答案 {question_id: answer}")
    score = Column(Integer, nullable=True, comment="得分")
    total_score = Column(Integer, default=0, comment="总分")
    time_spent = Column(Integer, default=0, comment="用时(秒)")
    grading_detail = Column(JSON, nullable=True, comment="自动批改详情")
    submitted_at = Column(DateTime, nullable=True, comment="提交时间")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
