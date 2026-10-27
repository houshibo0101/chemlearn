# -*- coding: utf-8 -*-
# Copyright (c) 2026 侯世勃. All rights reserved.
"""
做题记录与学习报告 API
- GET  /practice-records          做题历史（分页 + 筛选）
- GET  /practice-records/stats    统计概览（总做题/正确率/平均用时/7天趋势/连击）
- GET  /practice-records/trend    做题量与正确率趋势（默认14天）
- GET  /practice-records/knowledge 知识点掌握度（基于真实做题记录）
- GET  /practice-records/heatmap  学习活跃热力图
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, Question, PracticeRecord

router = APIRouter(prefix="/practice-records", tags=["做题记录"])


def _local_date(dt: datetime) -> str:
    """UTC 时间转中国时区日期字符串"""
    return (dt + timedelta(hours=8)).strftime("%Y-%m-%d")


async def _user_day_counts(db: AsyncSession, user_id: int, days: int):
    """取最近 N 天（含今天）用户的按天做题/正确计数。返回 {date_str: [total, correct]}"""
    start = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(PracticeRecord.submitted_at, PracticeRecord.is_correct).where(
            PracticeRecord.user_id == user_id,
            PracticeRecord.submitted_at >= start,
        )
    )).all()
    agg = defaultdict(lambda: [0, 0])
    for ts, correct in rows:
        d = _local_date(ts)
        agg[d][0] += 1
        if correct:
            agg[d][1] += 1
    return agg


def _day_list(days: int):
    """最近 N 天（含今天）的日期字符串列表，旧→新"""
    today = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _calc_streak(agg) -> int:
    """连续学习天数：从今天（或昨天）往前数有做题记录的天数"""
    streak = 0
    today = (datetime.now(timezone.utc) + timedelta(hours=8)).date()
    for i in range(0, 366):
        d = (today - timedelta(days=i)).isoformat()
        if agg.get(d, [0])[0] > 0:
            streak += 1
        elif i == 0:
            continue  # 今天还没做不打断连击
        else:
            break
    return streak


# ========== 做题历史（分页） ==========

@router.get("", summary="做题历史（分页）")
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str = Query(None, description="practice/assignment/exam"),
    question_type: str = Query(None, description="题型筛选"),
    is_correct: str = Query(None, description="1 正确 / 0 错误"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conds = [PracticeRecord.user_id == current_user.id]
    if source:
        conds.append(PracticeRecord.source == source)
    if is_correct is not None and is_correct != "":
        # 前端传 "1"/"0" 字符串，注意 "0" 的 truthy 陷阱
        try:
            conds.append(PracticeRecord.is_correct == (int(is_correct) == 1))
        except ValueError:
            pass
    if question_type:
        conds.append(Question.question_type == question_type)

    base = select(PracticeRecord).join(Question, PracticeRecord.question_id == Question.id)
    total = (await db.execute(select(func.count()).select_from(
        base.where(*conds).subquery()
    ))).scalar() or 0

    rows = (await db.execute(
        base.where(*conds)
        .order_by(PracticeRecord.submitted_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    # 批量取题目信息
    qids = list({r.question_id for r in rows})
    qmap = {}
    if qids:
        qs = (await db.execute(
            select(Question.id, Question.title, Question.knowledge_point,
                   Question.question_type, Question.difficulty).where(Question.id.in_(qids))
        )).all()
        for qid, title, kp, qtype, diff in qs:
            qmap[qid] = {
                "question_title": title or "(无题干)",
                "knowledge_point": kp,
                "question_type": qtype.value if hasattr(qtype, "value") else qtype,
                "difficulty": diff,
            }

    items = []
    for r in rows:
        q = qmap.get(r.question_id, {})
        items.append({
            "id": r.id,
            "question_id": r.question_id,
            "question_title": q.get("question_title"),
            "knowledge_point": q.get("knowledge_point"),
            "question_type": q.get("question_type"),
            "difficulty": q.get("difficulty"),
            "source": r.source,
            "is_correct": bool(r.is_correct),
            "score": r.score,
            "total_score": r.total_score,
            "time_spent": r.time_spent,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ========== 统计概览 ==========

@router.get("/stats", summary="做题统计概览")
async def records_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(
        select(func.count(PracticeRecord.id)).where(PracticeRecord.user_id == current_user.id)
    )).scalar() or 0
    correct = (await db.execute(
        select(func.count(PracticeRecord.id)).where(
            PracticeRecord.user_id == current_user.id,
            PracticeRecord.is_correct == True,  # noqa: E712
        )
    )).scalar() or 0
    avg_time = (await db.execute(
        select(func.avg(PracticeRecord.time_spent)).where(
            PracticeRecord.user_id == current_user.id,
            PracticeRecord.time_spent.isnot(None),
        )
    )).scalar()

    agg = await _user_day_counts(db, current_user.id, 7)
    weekly_trend = [
        {"date": d, "total": agg.get(d, [0, 0])[0], "correct": agg.get(d, [0, 0])[1]}
        for d in _day_list(7)
    ]

    return {
        "total_questions": total,
        "correct_count": correct,
        "accuracy": round(correct / total * 100, 1) if total else 0,
        "avg_time_spent": round(avg_time) if avg_time else 0,
        "today_count": agg.get(_day_list(1)[-1], [0, 0])[0],
        "streak_days": _calc_streak(agg),
        "weekly_trend": weekly_trend,
    }


# ========== 趋势 ==========

@router.get("/trend", summary="做题量与正确率趋势")
async def records_trend(
    days: int = Query(14, ge=7, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agg = await _user_day_counts(db, current_user.id, days)
    trend = []
    for d in _day_list(days):
        total, correct = agg.get(d, [0, 0])
        trend.append({
            "date": d,
            "total": total,
            "correct": correct,
            "accuracy": round(correct / total * 100, 1) if total else 0,
        })
    return {"days": days, "trend": trend}


# ========== 知识点掌握度（基于真实做题记录） ==========

@router.get("/knowledge", summary="知识点掌握度（真实做题数据）")
async def records_knowledge(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Question.knowledge_point, PracticeRecord.is_correct).join(
            Question, PracticeRecord.question_id == Question.id
        ).where(PracticeRecord.user_id == current_user.id)
    )).all()

    agg = defaultdict(lambda: [0, 0])  # kp -> [total, correct]
    no_kp = [0, 0]
    for kp, correct in rows:
        bucket = agg[kp] if kp else no_kp
        bucket[0] += 1
        if correct:
            bucket[1] += 1

    details = []
    for kp, (total, correct) in agg.items():
        accuracy = round(correct / total * 100, 1)
        if accuracy >= 80:
            level, mastery = 3, "已掌握"
        elif accuracy >= 60:
            level, mastery = 2, "基本掌握"
        else:
            level, mastery = 1, "薄弱"
        details.append({
            "knowledge_point": kp,
            "total_done": total,
            "correct_count": correct,
            "accuracy": accuracy,
            "mastery": mastery,
            "level": level,
        })
    details.sort(key=lambda x: (x["accuracy"], -x["total_done"]))  # 薄弱在前

    total_done = sum(d[0] for d in agg.values()) + no_kp[0]
    total_correct = sum(d[1] for d in agg.values()) + no_kp[1]
    return {
        "total_done": total_done,
        "total_correct": total_correct,
        "overall_accuracy": round(total_correct / total_done * 100, 1) if total_done else 0,
        "knowledge_points_count": len(details),
        "weak_points": [d["knowledge_point"] for d in details if d["level"] == 1],
        "mastered_points": [d["knowledge_point"] for d in details if d["level"] == 3],
        "details": details,
    }


# ========== 学习活跃热力图 ==========

@router.get("/heatmap", summary="学习活跃热力图")
async def records_heatmap(
    days: int = Query(91, ge=28, le=366),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agg = await _user_day_counts(db, current_user.id, days)
    cells = [{"date": d, "count": agg.get(d, [0, 0])[0]} for d in _day_list(days)]
    active_days = sum(1 for c in cells if c["count"] > 0)
    return {
        "days": days,
        "active_days": active_days,
        "max_count": max((c["count"] for c in cells), default=0),
        "cells": cells,
    }
