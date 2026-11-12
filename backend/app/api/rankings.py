# -*- coding: utf-8 -*-
"""考试排名 API

前端契约（之前后端没实现，点「排名」直接 404）：
  GET /rankings/exam/{exam_id}          排名统计 +（教师/管理员）明细
  GET /rankings/exam/{exam_id}/export   导出排名 CSV

权限：
  · 管理员、考试创建老师：可看完整排名与导出
  · 学生：只有已提交该考试才能看自己的名次（不返回其他学生姓名）
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Exam, ExamSubmission, User, UserRole

router = APIRouter(prefix="/rankings", tags=["考试排名"])

SCORE_BUCKETS = ("0-59", "60-69", "70-79", "80-89", "90-100")


def _display_name(user: User) -> str:
    return user.full_name or user.username or ("学生%d" % user.id)


def _time_spent(submission: ExamSubmission) -> int:
    """答题用时（秒）；没有开始时间就记 0"""
    if submission.started_at and submission.submitted_at:
        try:
            return max(0, int((submission.submitted_at - submission.started_at).total_seconds()))
        except Exception:
            return 0
    return 0


def _is_manager(user: User, exam: Exam) -> bool:
    return user.role == UserRole.ADMIN or exam.teacher_id == user.id


async def _load_ranking(db: AsyncSession, exam_id: int):
    """返回 (exam, [(submission, user), ...])，按得分降序、用时升序、提交时间升序。

    同一学生多次提交只保留最好的一次，避免重复占名次。
    """
    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")

    rows = (await db.execute(
        select(ExamSubmission, User)
        .join(User, User.id == ExamSubmission.student_id)
        .where(
            ExamSubmission.exam_id == exam_id,
            ExamSubmission.score.is_not(None),
            ExamSubmission.submitted_at.is_not(None),
        )
    )).all()

    best = {}
    for submission, user in rows:
        current = best.get(user.id)
        if current is None:
            best[user.id] = (submission, user)
            continue
        cur_sub = current[0]
        # 分数优先，其次用时短
        if ((submission.score or 0), -_time_spent(submission)) > (
                (cur_sub.score or 0), -_time_spent(cur_sub)):
            best[user.id] = (submission, user)

    ordered = sorted(
        best.values(),
        key=lambda pair: (-(pair[0].score or 0),
                          _time_spent(pair[0]),
                          pair[0].submitted_at),
    )
    return exam, ordered


def _ranked_items(ordered):
    """并列同分同名次（1,2,2,4 这种）"""
    items = []
    last_score = None
    rank = 0
    for index, (submission, user) in enumerate(ordered):
        score = submission.score or 0
        if score != last_score:
            rank = index + 1
            last_score = score
        items.append({
            "rank": rank,
            "student_id": user.id,
            "student_name": _display_name(user),
            "username": user.username,
            "score": score,
            "time_spent": _time_spent(submission),
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        })
    return items


def _score_distribution(ordered, total_score: int):
    buckets = {label: 0 for label in SCORE_BUCKETS}
    for submission, _user in ordered:
        score = submission.score or 0
        percent = (score / total_score * 100) if total_score else 0
        if percent < 60:
            buckets["0-59"] += 1
        elif percent < 70:
            buckets["60-69"] += 1
        elif percent < 80:
            buckets["70-79"] += 1
        elif percent < 90:
            buckets["80-89"] += 1
        else:
            buckets["90-100"] += 1
    return buckets


def _summary(exam: Exam, ordered):
    scores = [submission.score or 0 for submission, _user in ordered]
    participant_count = len(scores)
    avg_score = round(sum(scores) / participant_count, 1) if participant_count else 0
    return {
        "exam_id": exam.id,
        "exam_title": exam.title,
        "total_score": exam.total_score,
        "participant_count": participant_count,
        "avg_score": avg_score,
        "max_score": max(scores) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "score_distribution": _score_distribution(ordered, exam.total_score),
    }


@router.get("/exam/{exam_id}", summary="考试排名")
async def exam_ranking(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exam, ordered = await _load_ranking(db, exam_id)
    manager = _is_manager(current_user, exam)

    my_rank = None
    my_score = None
    my_time_spent = 0
    for item in _ranked_items(ordered):
        if item["student_id"] == current_user.id:
            my_rank = item["rank"]
            my_score = item["score"]
            my_time_spent = item["time_spent"]
            break

    if not manager and my_rank is None:
        raise HTTPException(status_code=403, detail="只有参加并提交过该考试的学生才能查看排名")

    payload = _summary(exam, ordered)
    payload.update({
        "my_rank": my_rank,
        "my_score": my_score,
        "my_time_spent": my_time_spent,
        # 学生只看自己的名次与统计，不暴露其他学生信息
        "ranking": _ranked_items(ordered) if manager else [],
    })
    return payload


@router.get("/exam/{exam_id}/export", summary="导出考试排名 CSV")
async def export_exam_ranking(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exam, ordered = await _load_ranking(db, exam_id)
    if not _is_manager(current_user, exam):
        raise HTTPException(status_code=403, detail="只有考试创建老师或管理员可以导出排名")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["排名", "学生姓名", "账号", "得分", "用时(秒)", "提交时间"])
    for item in _ranked_items(ordered):
        writer.writerow([
            item["rank"],
            item["student_name"],
            item["username"],
            item["score"],
            item["time_spent"],
            (item["submitted_at"] or "").replace("T", " ")[:19],
        ])

    # 带 BOM，Excel 直接打开不乱码
    content = ("\ufeff" + buffer.getvalue()).encode("utf-8")
    filename = "exam-%d-ranking.csv" % exam.id
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )
