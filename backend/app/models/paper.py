"""
套卷（整份试卷）模型

与 exams 的区别：
  exams   = 教师从题库挑题组卷，按班级发布，有开始/结束时间；
  papers  = 整份高考卷 PDF 上传 → AI 结构化 → 生成独立 HTML 做题页，
            不限时间窗口，谁都能练，做完错题直接进错题本。

题目本身仍然写进 questions 表（source 字段标记来源套卷），
这样错题本、学习报告、知识点统计都能复用现有逻辑。
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Enum,
)
from app.core.database import Base


class PaperStatus(str, enum.Enum):
    """审核状态：学生上传的卷子必须审核通过才会生成"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaperGenStatus(str, enum.Enum):
    """生成状态：AI 结构化 + 渲染 HTML 的过程"""
    WAITING = "waiting"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, comment="试卷标题，如 2024年广东省高考化学")
    province = Column(String(32), nullable=True, comment="省份")
    year = Column(Integer, nullable=True, comment="年份")
    exam_type = Column(String(32), default="高考真题", comment="类型：高考真题/模拟/联考/其他")

    source_filename = Column(String(255), nullable=True, comment="上传时的原始文件名")
    source_path = Column(String(512), nullable=True, comment="PDF 存放路径（相对 uploads）")
    file_size = Column(Integer, nullable=True, comment="文件字节数")

    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(PaperStatus), default=PaperStatus.PENDING, nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True, comment="驳回原因 / 审核备注")
    reviewed_at = Column(DateTime, nullable=True)

    duration = Column(Integer, default=75, comment="建议时长（分钟）")
    total_score = Column(Integer, default=100, comment="总分")
    question_count = Column(Integer, default=0)

    # 题目快照：生成 HTML 与后续重新渲染都读这里，不依赖 questions 表
    questions_json = Column(JSON, nullable=True, comment="结构化题目数组")
    html_path = Column(String(512), nullable=True, comment="生成的做题页（相对 uploads）")

    gen_status = Column(Enum(PaperGenStatus), default=PaperGenStatus.WAITING, nullable=False)
    gen_error = Column(Text, nullable=True)
    gen_at = Column(DateTime, nullable=True)

    # 生成过程可视化：前端据此显示进度条 + 当前步骤 + 实时日志
    progress = Column(Integer, default=0, comment="生成进度 0-100")
    progress_text = Column(String(120), nullable=True, comment="当前步骤")
    gen_logs = Column(JSON, nullable=True, comment="最近若干条生成日志 [{t, m}]")

    is_public = Column(Boolean, default=True, comment="是否所有学生可见")
    view_count = Column(Integer, default=0)
    attempt_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class PaperAttempt(Base):
    """一次作答记录（限时练习的结果）

    status 区分「进行中」和「已交卷」：进行中的记录保存服务端开始时间，
    刷新页面/切后台都不会重置或放慢倒计时（前端拿服务端时间算剩余）。
    """
    __tablename__ = "paper_attempts"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(16), default="submitted", nullable=False, comment="doing/submitted")
    started_at = Column(DateTime, nullable=True, comment="开始答题时间（服务端）")
    switch_count = Column(Integer, default=0, comment="切屏次数（反作弊）")
    overtime = Column(Boolean, default=False, comment="是否超时提交")

    answers = Column(JSON, default=dict, comment="作答内容 {题号: 答案}")
    score = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    wrong_count = Column(Integer, default=0)
    duration_sec = Column(Integer, default=0, comment="实际用时（秒）")
    # 未判分的题型（填空/计算）靠学生自评，这里记录自评结果
    self_judge = Column(JSON, nullable=True, comment="{题号: true/false}")

    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
