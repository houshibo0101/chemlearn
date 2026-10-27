"""
考试管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.question import Question
from app.models.exam import Exam, ExamClass, ExamQuestion, ExamSubmission, ExamStatus
from app.models.class_room import TeacherClass

router = APIRouter(prefix="/exams", tags=["考试管理"])


class ExamQuestionItem(BaseModel):
    question_id: int
    score: int = 5


class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: List[ExamQuestionItem] = []
    class_ids: List[int] = []
    duration: int = 60
    total_score: int = 100
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class ExamSubmit(BaseModel):
    answers: dict


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_exams(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取考试列表"""
    query = select(Exam)

    if current_user.role == UserRole.TEACHER:
        # 老师能看到：自己创建的 + 布置给自己管理班级的
        my_class_ids = (await db.execute(
            select(TeacherClass.class_id).where(TeacherClass.teacher_id == current_user.id)
        )).scalars().all()
        class_exam_ids = []
        if my_class_ids:
            class_exam_ids = (await db.execute(
                select(ExamClass.exam_id).where(ExamClass.class_id.in_(my_class_ids))
            )).scalars().all()
        from sqlalchemy import or_
        query = query.where(or_(
            Exam.teacher_id == current_user.id,
            Exam.id.in_(class_exam_ids) if class_exam_ids else False
        ))
    elif current_user.role == UserRole.STUDENT:
        if current_user.class_id:
            class_exam_ids = (await db.execute(
                select(ExamClass.exam_id).where(ExamClass.class_id == current_user.class_id)
            )).scalars().all()
            query = query.where(Exam.id.in_(class_exam_ids), Exam.status == ExamStatus.PUBLISHED)
        else:
            return {"items": [], "total": 0}

    result = await db.execute(query.order_by(Exam.created_at.desc()))
    exams = result.scalars().all()

    items = []
    for e in exams:
        class_ids = (await db.execute(
            select(ExamClass.class_id).where(ExamClass.exam_id == e.id)
        )).scalars().all()

        submission = None
        if current_user.role == UserRole.STUDENT:
            submission = (await db.execute(
                select(ExamSubmission).where(
                    ExamSubmission.exam_id == e.id,
                    ExamSubmission.student_id == current_user.id,
                )
            )).scalar_one_or_none()

        items.append({
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "duration": e.duration,
            "total_score": e.total_score,
            "class_ids": class_ids,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "status": e.status.value,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "submitted": submission is not None,
            "score": submission.score if submission else None,
        })
    return {"items": items, "total": len(items)}


@router.post("")
async def create_exam(
    data: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建考试（老师）"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可创建考试")

    exam = Exam(
        title=data.title,
        description=data.description,
        teacher_id=current_user.id,
        duration=data.duration,
        total_score=data.total_score,
        start_time=datetime.fromisoformat(data.start_time) if data.start_time else None,
        end_time=datetime.fromisoformat(data.end_time) if data.end_time else None,
        status=ExamStatus.DRAFT,
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    # 添加题目
    for i, q in enumerate(data.questions):
        db.add(ExamQuestion(exam_id=exam.id, question_id=q.question_id, order=i, score=q.score))

    # 关联班级
    for cid in data.class_ids:
        db.add(ExamClass(exam_id=exam.id, class_id=cid))
    await db.commit()

    return {"id": exam.id, "message": "创建成功"}


@router.post("/{exam_id}/publish")
async def publish_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布考试"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可发布")

    e = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "考试不存在")
    # 权限：创建者 或 考试关联班级的老师
    if e.teacher_id != current_user.id:
        e_class_ids = (await db.execute(
            select(ExamClass.class_id).where(ExamClass.exam_id == e.id)
        )).scalars().all()
        if e_class_ids:
            is_class_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id.in_(e_class_ids)
                )
            )).scalar_one_or_none()
            if not is_class_teacher:
                raise HTTPException(403, "无权限")
        else:
            raise HTTPException(403, "无权限")

    previous_status = e.status
    e.status = ExamStatus.PUBLISHED
    await db.commit()

    # 站内通知：发给关联班级的学生（仅首次发布时发，避免重复发布刷屏）
    if previous_status != ExamStatus.PUBLISHED:
        from app.api.notifications import notify_users
        e_class_ids = (await db.execute(
            select(ExamClass.class_id).where(ExamClass.exam_id == e.id)
        )).scalars().all()
        if e_class_ids:
            student_ids = (await db.execute(
                select(User.id).where(
                    User.role == UserRole.STUDENT,
                    User.class_id.in_(e_class_ids),
                )
            )).scalars().all()
            await notify_users(
                db, student_ids,
                title=f"新考试：{e.title}",
                content="老师发布了新考试，点击前往「我的考试」开始作答。",
                ntype="exam", related_id=e.id,
            )
    return {"message": "发布成功"}


@router.get("/{exam_id}")
async def get_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取考试详情（含题目）"""
    e = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "考试不存在")

    exam_questions = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.order)
    )).scalars().all()

    questions = []
    for eq in exam_questions:
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q:
            questions.append({
                "id": q.id,
                "question_code": q.question_code,
                "title": q.title,
                "content": q.content,
                "question_type": q.question_type,
                "difficulty": q.difficulty,
                "options": q.options,
                "score": eq.score,
            })

    return {
        "id": e.id,
        "title": e.title,
        "description": e.description,
        "duration": e.duration,
        "total_score": e.total_score,
        "questions": questions,
        "start_time": e.start_time.isoformat() if e.start_time else None,
        "end_time": e.end_time.isoformat() if e.end_time else None,
        "status": e.status.value,
    }


@router.post("/{exam_id}/start")
async def start_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生开始考试"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(403, "仅学生可参加考试")

    e = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "考试不存在")
    if e.status != ExamStatus.PUBLISHED:
        raise HTTPException(400, "考试未发布")

    # 创建或更新提交记录
    submission = (await db.execute(
        select(ExamSubmission).where(
            ExamSubmission.exam_id == exam_id,
            ExamSubmission.student_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not submission:
        submission = ExamSubmission(
            exam_id=exam_id,
            student_id=current_user.id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(submission)
        await db.commit()
        await db.refresh(submission)

    return {"submission_id": submission.id, "started_at": submission.started_at.isoformat()}


@router.post("/{exam_id}/submit")
async def submit_exam(
    exam_id: int,
    data: ExamSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生提交考试"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(403, "仅学生可提交")

    submission = (await db.execute(
        select(ExamSubmission).where(
            ExamSubmission.exam_id == exam_id,
            ExamSubmission.student_id == current_user.id,
        )
    )).scalar_one_or_none()

    if not submission:
        raise HTTPException(400, "请先开始考试")
    if submission.submitted_at:
        raise HTTPException(400, "已提交，不能重复提交")

    # 自动判分
    exam_questions = (await db.execute(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id)
    )).scalars().all()

    score = 0
    for eq in exam_questions:
        q = (await db.execute(select(Question).where(Question.id == eq.question_id))).scalar_one_or_none()
        if q and str(data.answers.get(str(q.id), "")).strip() == str(q.answer).strip():
            score += eq.score

    submission.answers = data.answers
    submission.score = score
    submission.submitted_at = datetime.now(timezone.utc)
    await db.commit()

    return {"score": score, "message": "提交成功"}


@router.get("/{exam_id}/submissions")
async def get_exam_submissions(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """老师查看考试成绩"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可查看")

    # 权限：创建者 或 考试关联班级的老师
    e = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "考试不存在")
    if e.teacher_id != current_user.id:
        e_class_ids = (await db.execute(
            select(ExamClass.class_id).where(ExamClass.exam_id == e.id)
        )).scalars().all()
        if e_class_ids:
            is_class_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id.in_(e_class_ids)
                )
            )).scalar_one_or_none()
            if not is_class_teacher:
                raise HTTPException(403, "无权限")
        else:
            raise HTTPException(403, "无权限")

    submissions = (await db.execute(
        select(ExamSubmission).where(ExamSubmission.exam_id == exam_id)
    )).scalars().all()

    items = []
    for s in submissions:
        student = (await db.execute(select(User).where(User.id == s.student_id))).scalar_one_or_none()
        items.append({
            "id": s.id,
            "student_id": s.student_id,
            "student_name": student.full_name if student else (student.username if student else "未知"),
            "score": s.score,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        })

    # 按分数排序
    items.sort(key=lambda x: x["score"] or 0, reverse=True)
    return {"items": items, "total": len(items)}


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除考试"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可删除")

    e = (await db.execute(select(Exam).where(Exam.id == exam_id))).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "考试不存在")
    # 权限：创建者 或 考试关联班级的老师
    if e.teacher_id != current_user.id:
        e_class_ids = (await db.execute(
            select(ExamClass.class_id).where(ExamClass.exam_id == e.id)
        )).scalars().all()
        if e_class_ids:
            is_class_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id.in_(e_class_ids)
                )
            )).scalar_one_or_none()
            if not is_class_teacher:
                raise HTTPException(403, "无权限")
        else:
            raise HTTPException(403, "无权限")

    await db.execute(delete(ExamClass).where(ExamClass.exam_id == exam_id))
    await db.execute(delete(ExamQuestion).where(ExamQuestion.exam_id == exam_id))
    await db.execute(delete(ExamSubmission).where(ExamSubmission.exam_id == exam_id))
    await db.delete(e)
    await db.commit()
    return {"message": "删除成功"}
