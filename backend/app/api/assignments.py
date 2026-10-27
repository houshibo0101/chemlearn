"""
作业管理 API
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
from app.models.assignment import Assignment, AssignmentClass, AssignmentSubmission, AssignmentStatus
from app.models.class_room import TeacherClass

router = APIRouter(prefix="/assignments", tags=["作业管理"])


class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    question_ids: List[int] = []
    class_ids: List[int] = []
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class AssignmentSubmit(BaseModel):
    answers: dict


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("")
async def list_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取作业列表"""
    query = select(Assignment)

    if current_user.role == UserRole.TEACHER:
        # 老师能看到：自己创建的 + 布置给自己管理班级的
        my_class_ids = (await db.execute(
            select(TeacherClass.class_id).where(TeacherClass.teacher_id == current_user.id)
        )).scalars().all()
        class_assign_ids = []
        if my_class_ids:
            class_assign_ids = (await db.execute(
                select(AssignmentClass.assignment_id).where(AssignmentClass.class_id.in_(my_class_ids))
            )).scalars().all()
        # 并集：自己创建的 OR 布置给我管理班级的
        from sqlalchemy import or_
        query = query.where(or_(
            Assignment.teacher_id == current_user.id,
            Assignment.id.in_(class_assign_ids) if class_assign_ids else False
        ))
    elif current_user.role == UserRole.STUDENT:
        # 学生只能看到自己班级的作业
        if current_user.class_id:
            class_assign_ids = (await db.execute(
                select(AssignmentClass.assignment_id).where(AssignmentClass.class_id == current_user.class_id)
            )).scalars().all()
            query = query.where(Assignment.id.in_(class_assign_ids), Assignment.status == AssignmentStatus.PUBLISHED)
        else:
            return {"items": [], "total": 0}

    result = await db.execute(query.order_by(Assignment.created_at.desc()))
    assignments = result.scalars().all()

    items = []
    for a in assignments:
        # 获取关联班级
        class_ids = (await db.execute(
            select(AssignmentClass.class_id).where(AssignmentClass.assignment_id == a.id)
        )).scalars().all()

        # 学生查看提交状态
        submission = None
        if current_user.role == UserRole.STUDENT:
            submission = (await db.execute(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id == a.id,
                    AssignmentSubmission.student_id == current_user.id,
                )
            )).scalar_one_or_none()

        items.append({
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "question_count": len(a.question_ids or []),
            "class_ids": class_ids,
            "start_time": a.start_time.isoformat() if a.start_time else None,
            "end_time": a.end_time.isoformat() if a.end_time else None,
            "status": a.status.value,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "submitted": submission is not None,
            "score": submission.score if submission else None,
        })
    return {"items": items, "total": len(items)}


@router.post("")
async def create_assignment(
    data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建作业（老师）"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可创建作业")

    assignment = Assignment(
        title=data.title,
        description=data.description,
        teacher_id=current_user.id,
        question_ids=data.question_ids,
        start_time=datetime.fromisoformat(data.start_time) if data.start_time else None,
        end_time=datetime.fromisoformat(data.end_time) if data.end_time else None,
        status=AssignmentStatus.DRAFT,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    # 关联班级
    for cid in data.class_ids:
        db.add(AssignmentClass(assignment_id=assignment.id, class_id=cid))
    await db.commit()

    return {"id": assignment.id, "message": "创建成功"}


@router.post("/{assignment_id}/publish")
async def publish_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发布作业"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可发布")

    a = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "作业不存在")
    # 权限：创建者 或 作业关联班级的老师
    if a.teacher_id != current_user.id:
        a_class_ids = (await db.execute(
            select(AssignmentClass.class_id).where(AssignmentClass.assignment_id == a.id)
        )).scalars().all()
        if a_class_ids:
            is_class_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id.in_(a_class_ids)
                )
            )).scalar_one_or_none()
            if not is_class_teacher:
                raise HTTPException(403, "无权限")
        else:
            raise HTTPException(403, "无权限")

    previous_status = a.status
    a.status = AssignmentStatus.PUBLISHED
    await db.commit()

    # 站内通知：发给关联班级的学生（仅首次发布时发，避免重复发布刷屏）
    if previous_status != AssignmentStatus.PUBLISHED:
        from app.api.notifications import notify_users
        a_class_ids = (await db.execute(
            select(AssignmentClass.class_id).where(AssignmentClass.assignment_id == a.id)
        )).scalars().all()
        if a_class_ids:
            student_ids = (await db.execute(
                select(User.id).where(
                    User.role == UserRole.STUDENT,
                    User.class_id.in_(a_class_ids),
                )
            )).scalars().all()
            await notify_users(
                db, student_ids,
                title=f"新作业：{a.title}",
                content="老师发布了新作业，记得在截止时间前完成哦！",
                ntype="assignment", related_id=a.id,
            )
    return {"message": "发布成功"}


@router.get("/{assignment_id}")
async def get_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取作业详情（含题目）"""
    a = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "作业不存在")

    # 获取题目详情
    questions = []
    if a.question_ids:
        qs = (await db.execute(select(Question).where(Question.id.in_(a.question_ids)))).scalars().all()
        q_map = {q.id: q for q in qs}
        for qid in a.question_ids:
            q = q_map.get(qid)
            if q:
                questions.append({
                    "id": q.id,
                    "question_code": q.question_code,
                    "title": q.title,
                    "content": q.content,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "options": q.options,
                })

    return {
        "id": a.id,
        "title": a.title,
        "description": a.description,
        "questions": questions,
        "start_time": a.start_time.isoformat() if a.start_time else None,
        "end_time": a.end_time.isoformat() if a.end_time else None,
        "status": a.status.value,
    }


@router.post("/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: int,
    data: AssignmentSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生提交作业"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(403, "仅学生可提交")

    a = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "作业不存在")
    if a.status != AssignmentStatus.PUBLISHED:
        raise HTTPException(400, "作业未发布")

    # 自动判分
    score = 0
    total = len(a.question_ids or [])
    if a.question_ids:
        qs = (await db.execute(select(Question).where(Question.id.in_(a.question_ids)))).scalars().all()
        q_map = {q.id: q for q in qs}
        for qid in a.question_ids:
            q = q_map.get(qid)
            if q and str(data.answers.get(str(qid), "")).strip() == str(q.answer).strip():
                score += 1

    # 保存提交
    existing = (await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == current_user.id,
        )
    )).scalar_one_or_none()

    if existing:
        existing.answers = data.answers
        existing.score = score
        existing.total_score = total
        existing.submitted_at = datetime.now(timezone.utc)
    else:
        db.add(AssignmentSubmission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            answers=data.answers,
            score=score,
            total_score=total,
            submitted_at=datetime.now(timezone.utc),
        ))
    await db.commit()

    return {"score": score, "total": total, "message": "提交成功"}


@router.get("/{assignment_id}/submissions")
async def get_submissions(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """老师查看作业提交情况"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可查看")

    # 权限：创建者 或 作业关联班级的老师
    a = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "作业不存在")
    if a.teacher_id != current_user.id:
        a_class_ids = (await db.execute(
            select(AssignmentClass.class_id).where(AssignmentClass.assignment_id == a.id)
        )).scalars().all()
        if a_class_ids:
            is_class_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id.in_(a_class_ids)
                )
            )).scalar_one_or_none()
            if not is_class_teacher:
                raise HTTPException(403, "无权限")
        else:
            raise HTTPException(403, "无权限")

    submissions = (await db.execute(
        select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id)
    )).scalars().all()

    items = []
    for s in submissions:
        student = (await db.execute(select(User).where(User.id == s.student_id))).scalar_one_or_none()
        items.append({
            "id": s.id,
            "student_id": s.student_id,
            "student_name": student.full_name if student else student.username if student else "未知",
            "score": s.score,
            "total_score": s.total_score,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        })
    return {"items": items, "total": len(items)}


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除作业"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(403, "仅老师可删除")

    a = (await db.execute(select(Assignment).where(Assignment.id == assignment_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "作业不存在")
    # 权限：创建者 或 作业关联班级的老师
    if a.teacher_id != current_user.id:
        a_class_ids = (await db.execute(
            select(AssignmentClass.class_id).where(AssignmentClass.assignment_id == a.id)
        )).scalars().all()
        if a_class_ids:
            is_class_teacher = (await db.execute(
                select(TeacherClass).where(
                    TeacherClass.teacher_id == current_user.id,
                    TeacherClass.class_id.in_(a_class_ids)
                )
            )).scalar_one_or_none()
            if not is_class_teacher:
                raise HTTPException(403, "无权限")
        else:
            raise HTTPException(403, "无权限")

    await db.execute(delete(AssignmentClass).where(AssignmentClass.assignment_id == assignment_id))
    await db.execute(delete(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id))
    await db.delete(a)
    await db.commit()
    return {"message": "删除成功"}
