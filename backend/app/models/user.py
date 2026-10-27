"""
用户模型
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean
from app.core.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(64), nullable=True, comment="姓名")
    grade = Column(String(32), nullable=True, comment="学段，如高一/高二/高三")
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    class_id = Column(Integer, nullable=True, comment="学生所属班级ID")
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False, comment="首次登录是否强制改密")
    tag = Column(String(32), default="normal", comment="账号标签：normal正常/suspicious数据异常/banned已封禁")
    api_call_count = Column(Integer, default=0, comment="API调用总次数")
    allowed_api_scopes = Column(String(128), default="all,question,ai", comment="允许创建的API Key权限范围，逗号分隔")
    daily_limit = Column(Integer, default=1000, comment="API每日调用默认额度")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
