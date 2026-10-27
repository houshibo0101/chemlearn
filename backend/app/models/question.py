"""
题目模型（管理员上传）
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class QuestionType(str, enum.Enum):
    SINGLE = "single"      # 单选
    MULTIPLE = "multiple"  # 多选
    FILL = "fill"          # 填空
    CALCULATION = "calculation"  # 计算
    SUBJECTIVE = "subjective"  # 简答题


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_code = Column(String(32), unique=True, index=True, nullable=True, comment="题目唯一编号，如Q0001")
    title = Column(String(512), nullable=False, comment="题目标题/题干")
    content = Column(Text, nullable=True, comment="题目详细内容")
    # values_callable: 数据库按枚举值(single/multiple/...)存取，
    # 与 import_gaokao_unified.py 裸导入的题库数据及前端筛选参数保持一致
    question_type = Column(Enum(QuestionType, values_callable=lambda x: [e.value for e in x]), default=QuestionType.SINGLE, nullable=False)
    difficulty = Column(Enum(Difficulty, values_callable=lambda x: [e.value for e in x]), default=Difficulty.MEDIUM, nullable=False)
    grade = Column(String(32), nullable=True, comment="适用学段")
    knowledge_point = Column(String(128), nullable=True, comment="知识点")
    options = Column(Text, nullable=True, comment="选项JSON，如[{\"key\":\"A\",\"text\":\"...\"}]")
    answer = Column(Text, nullable=False, comment="正确答案")
    analysis = Column(Text, nullable=True, comment="解析")
    images = Column(Text, nullable=True, comment="题目图片JSON数组，如[\"/uploads/q1.jpg\"]")
    keywords = Column(Text, nullable=True, comment="简答题得分关键词JSON，如[{\"word\":\"摩尔质量\",\"score\":2}]")
    source = Column(String(256), nullable=True, comment="题目来源，如2024年全国新课标卷第3题")
    sub_questions = Column(Text, nullable=True, comment="分小问JSON数组，如[{\"id\":1,\"content\":\"(1)...\",\"answer\":\"...\",\"keywords\":[...],\"score\":2}]")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[creator_id])
