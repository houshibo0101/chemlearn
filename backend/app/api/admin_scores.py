# -*- coding: utf-8 -*-
"""管理员成绩管理：查看并修改学生套卷 / 考试成绩。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.config import settings
from app.models import User, Paper, PaperAttempt, Exam, ExamSubmission

router = APIRouter(prefix="/admin/scores", tags=["管理员-成绩管理"])


def _iso(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _paper_item(attempt: PaperAttempt, paper: Paper, user: User) -> dict:
    return {
        "kind": "paper",
        "id": attempt.id,
        "student_id": user.id,
        "student_name": user.full_name or user.username,
        "username": user.username,
        "title": paper.title if paper else "套卷练习",
        "score": attempt.score if attempt.score is not None else 0,
        "total_score": attempt.total_score or (paper.total_score if paper else 0) or 0,
        "submitted_at": _iso(attempt.submitted_at),
        "status": attempt.status or "submitted",
    }


def _exam_item(submission: ExamSubmission, exam: Exam, user: User) -> dict:
    return {
        "kind": "exam",
        "id": submission.id,
        "student_id": user.id,
        "student_name": user.full_name or user.username,
        "username": user.username,
        "title": exam.title if exam else "考试",
        "score": submission.score if submission.score is not None else 0,
        "total_score": (exam.total_score if exam else 0) or 0,
        "submitted_at": _iso(submission.submitted_at),
        "status": "submitted",
    }


@router.get("", summary="学生成绩列表")
async def list_scores(
    kind: str = Query("paper", pattern="^(paper|exam)$"),
    keyword: str = Query("", max_length=60),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    keyword = keyword.strip()
    if kind == "paper":
        query = (
            select(PaperAttempt, Paper, User)
            .join(Paper, Paper.id == PaperAttempt.paper_id)
            .join(User, User.id == PaperAttempt.user_id)
            .where(PaperAttempt.status == "submitted")
        )
        count_query = (
            select(func.count(PaperAttempt.id))
            .join(Paper, Paper.id == PaperAttempt.paper_id)
            .join(User, User.id == PaperAttempt.user_id)
            .where(PaperAttempt.status == "submitted")
        )
        if keyword:
            like = f"%{keyword}%"
            cond = or_(User.username.like(like), User.full_name.like(like), Paper.title.like(like))
            query = query.where(cond)
            count_query = count_query.where(cond)
        total = (await db.execute(count_query)).scalar() or 0
        rows = (await db.execute(
            query.order_by(desc(PaperAttempt.submitted_at))
            .offset((page - 1) * page_size).limit(page_size)
        )).all()
        items = [_paper_item(attempt, paper, user) for attempt, paper, user in rows]
    else:
        query = (
            select(ExamSubmission, Exam, User)
            .join(Exam, Exam.id == ExamSubmission.exam_id)
            .join(User, User.id == ExamSubmission.student_id)
            .where(ExamSubmission.submitted_at.isnot(None))
        )
        count_query = (
            select(func.count(ExamSubmission.id))
            .join(Exam, Exam.id == ExamSubmission.exam_id)
            .join(User, User.id == ExamSubmission.student_id)
            .where(ExamSubmission.submitted_at.isnot(None))
        )
        if keyword:
            like = f"%{keyword}%"
            cond = or_(User.username.like(like), User.full_name.like(like), Exam.title.like(like))
            query = query.where(cond)
            count_query = count_query.where(cond)
        total = (await db.execute(count_query)).scalar() or 0
        rows = (await db.execute(
            query.order_by(desc(ExamSubmission.submitted_at))
            .offset((page - 1) * page_size).limit(page_size)
        )).all()
        items = [_exam_item(submission, exam, user) for submission, exam, user in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "kind": kind,
    }


class ScoreUpdate(BaseModel):
    score: int = Field(ge=0, le=1000, description="修改后的得分")


@router.put("/{kind}/{record_id}", summary="修改学生成绩")
async def update_score(
    kind: str,
    record_id: int,
    data: ScoreUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if admin.username != settings.HIDDEN_ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="只有专用后台账号可以修改分数")

    if kind == "paper":
        row = await db.get(PaperAttempt, record_id)
        if not row:
            raise HTTPException(status_code=404, detail="套卷作答记录不存在")
        paper = await db.get(Paper, row.paper_id)
        total = row.total_score or (paper.total_score if paper else 0) or 0
        user = await db.get(User, row.user_id)
        if data.score > total:
            raise HTTPException(status_code=400, detail=f"分数不能超过满分 {total}")
        row.score = data.score
        await db.commit()
        await db.refresh(row)
        return {"ok": True, "item": _paper_item(row, paper, user)}

    if kind == "exam":
        row = await db.get(ExamSubmission, record_id)
        if not row:
            raise HTTPException(status_code=404, detail="考试提交记录不存在")
        exam = await db.get(Exam, row.exam_id)
        total = (exam.total_score if exam else 0) or 0
        user = await db.get(User, row.student_id)
        if data.score > total:
            raise HTTPException(status_code=400, detail=f"分数不能超过满分 {total}")
        row.score = data.score
        await db.commit()
        await db.refresh(row)
        return {"ok": True, "item": _exam_item(row, exam, user)}

    raise HTTPException(status_code=400, detail="只支持 paper 或 exam")
