"""
班级模型
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.core.database import Base


class ClassRoom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False, comment="班级名称，如高一1班")
    grade = Column(String(32), nullable=True, comment="学段，高一/高二/高三")
    description = Column(String(255), nullable=True, comment="班级描述")
    join_code = Column(String(8), nullable=True, unique=True, index=True, comment="班级邀请码")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TeacherClass(Base):
    __tablename__ = "teacher_classes"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
