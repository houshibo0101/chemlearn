"""
考试模型
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum
from app.core.database import Base


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ONGOING = "ongoing"
    FINISHED = "finished"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), nullable=False, comment="考试标题")
    description = Column(Text, nullable=True, comment="考试说明")
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    duration = Column(Integer, default=60, comment="考试时长（分钟）")
    total_score = Column(Integer, default=100, comment="总分")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    status = Column(Enum(ExamStatus), default=ExamStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ExamClass(Base):
    __tablename__ = "exam_classes"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    order = Column(Integer, default=0, comment="题目顺序")
    score = Column(Integer, default=5, comment="每题分值")


class ExamSubmission(Base):
    __tablename__ = "exam_submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, default=dict, comment="学生答案")
    score = Column(Integer, nullable=True, comment="得分")
    started_at = Column(DateTime, nullable=True, comment="开始答题时间")
    submitted_at = Column(DateTime, nullable=True, comment="提交时间")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
