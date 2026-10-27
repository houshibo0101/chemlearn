"""
管理员数据看板 - 详细统计接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_admin
from app.models import User, UserRole, Question, WrongQuestion, APIKey, APICallLog

router = APIRouter(prefix="/admin/dashboard", tags=["管理员-数据看板"])


@router.get("/summary", summary="数据看板总览")
async def dashboard_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """获取数据看板总览数据"""
    # 用户统计
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    student_count = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.STUDENT))).scalar() or 0
    teacher_count = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.TEACHER))).scalar() or 0
    admin_count = (await db.execute(select(func.count(User.id)).where(User.role == UserRole.ADMIN))).scalar() or 0
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    banned_users = (await db.execute(select(func.count(User.id)).where(User.tag == "banned"))).scalar() or 0
    suspicious_users = (await db.execute(select(func.count(User.id)).where(User.tag == "suspicious"))).scalar() or 0

    # 题目统计
    total_questions = (await db.execute(select(func.count(Question.id)))).scalar() or 0

    # 错题统计
    total_wrong = (await db.execute(select(func.count(WrongQuestion.id)))).scalar() or 0

    # API Key统计
    total_api_keys = (await db.execute(select(func.count(APIKey.id)))).scalar() or 0
    active_api_keys = (await db.execute(select(func.count(APIKey.id)).where(APIKey.is_active == True))).scalar() or 0
    total_api_calls = (await db.execute(select(func.coalesce(func.sum(APIKey.call_count), 0)))).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "students": student_count,
            "teachers": teacher_count,
            "admins": admin_count,
            "active": active_users,
            "banned": banned_users,
            "suspicious": suspicious_users,
        },
        "questions": {
            "total": total_questions,
        },
        "wrong_questions": {
            "total": total_wrong,
        },
        "api": {
            "total_keys": total_api_keys,
            "active_keys": active_api_keys,
            "total_calls": total_api_calls,
        },
    }


@router.get("/users-by-grade", summary="用户按学段分布")
async def users_by_grade(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """用户按学段分布统计"""
    result = await db.execute(
        select(User.grade, func.count(User.id))
        .where(User.role == UserRole.STUDENT)
        .group_by(User.grade)
        .order_by(User.grade)
    )
    items = []
    for row in result.all():
        items.append({
            "grade": row[0] or "未设置",
            "count": row[1]
        })
    return {"items": items}


@router.get("/questions-by-difficulty", summary="题目按难度分布")
async def questions_by_difficulty(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """题目按难度分布统计"""
    result = await db.execute(
        select(Question.difficulty, func.count(Question.id))
        .group_by(Question.difficulty)
    )
    items = []
    diff_map = {"easy": "简单", "medium": "中等", "hard": "困难"}
    for row in result.all():
        items.append({
            "difficulty": diff_map.get(row[0], row[0] or "未设置"),
            "count": row[1]
        })
    return {"items": items}


@router.get("/questions-by-knowledge", summary="题目按知识点分布（Top10）")
async def questions_by_knowledge(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """题目按知识点分布统计"""
    result = await db.execute(
        select(Question.knowledge_point, func.count(Question.id))
        .where(Question.knowledge_point.isnot(None))
        .group_by(Question.knowledge_point)
        .order_by(func.count(Question.id).desc())
        .limit(limit)
    )
    items = []
    for row in result.all():
        items.append({
            "knowledge_point": row[0],
            "count": row[1]
        })
    return {"items": items}


@router.get("/top-wrong-questions", summary="错题最多的题目（Top10）")
async def top_wrong_questions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """错题次数最多的题目排行"""
    result = await db.execute(
        select(
            Question.id,
            Question.title,
            Question.knowledge_point,
            Question.difficulty,
            func.coalesce(func.sum(WrongQuestion.wrong_count), 0).label("total_wrong"),
            func.count(WrongQuestion.id).label("user_count")
        )
        .join(WrongQuestion, WrongQuestion.question_id == Question.id)
        .group_by(Question.id)
        .order_by(desc("total_wrong"))
        .limit(limit)
    )
    items = []
    for row in result.all():
        items.append({
            "question_id": row[0],
            "title": row[1][:50] + "..." if len(row[1] or "") > 50 else row[1],
            "knowledge_point": row[2],
            "difficulty": row[3],
            "total_wrong": row[4],
            "user_count": row[5],
        })
    return {"items": items}


@router.get("/top-active-users", summary="最活跃用户（Top10）")
async def top_active_users(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """错题最多的用户排行（活跃度指标）"""
    result = await db.execute(
        select(
            User.id,
            User.username,
            User.full_name,
            User.grade,
            func.count(WrongQuestion.id).label("wrong_count"),
            func.coalesce(func.sum(WrongQuestion.wrong_count), 0).label("total_wrong")
        )
        .join(WrongQuestion, WrongQuestion.user_id == User.id)
        .group_by(User.id)
        .order_by(desc("total_wrong"))
        .limit(limit)
    )
    items = []
    for row in result.all():
        items.append({
            "user_id": row[0],
            "username": row[1],
            "full_name": row[2],
            "grade": row[3],
            "wrong_count": row[4],
            "total_wrong": row[5],
        })
    return {"items": items}


@router.get("/api-call-logs", summary="API调用日志（最近）")
async def api_call_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """最近的API调用日志"""
    result = await db.execute(
        select(APICallLog)
        .order_by(APICallLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "endpoint": log.endpoint,
            "method": log.method,
            "ip": log.ip,
            "api_key": log.api_key,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return {"items": items, "total": len(items)}


@router.get("/api-key-stats", summary="API Key调用统计")
async def api_key_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """所有API Key的调用统计"""
    result = await db.execute(
        select(
            APIKey.id,
            APIKey.name,
            APIKey.user_id,
            User.username,
            APIKey.call_count,
            APIKey.daily_limit,
            APIKey.daily_call_count,
            APIKey.is_active,
            APIKey.created_at,
        )
        .join(User, User.id == APIKey.user_id)
        .order_by(APIKey.call_count.desc())
    )
    items = []
    for row in result.all():
        items.append({
            "key_id": row[0],
            "name": row[1],
            "user_id": row[2],
            "username": row[3],
            "call_count": row[4],
            "daily_limit": row[5],
            "daily_call_count": row[6],
            "is_active": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
        })
    return {"items": items, "total": len(items)}
