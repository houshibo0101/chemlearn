"""
学习统计与每日一题接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, WrongQuestion, Question
from app.services.cache_service import cache

router = APIRouter(prefix="/stats", tags=["学习统计"])


@router.get("/overview", summary="个人学习概览")
async def stats_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的学习统计概览"""
    # 总错题数
    wrong_count = (await db.execute(
        select(func.count(WrongQuestion.id)).where(WrongQuestion.user_id == current_user.id)
    )).scalar() or 0

    # 今日错题数
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_wrong = (await db.execute(
        select(func.count(WrongQuestion.id)).where(
            WrongQuestion.user_id == current_user.id,
            WrongQuestion.last_wrong_at >= today_start
        )
    )).scalar() or 0

    # 知识点统计
    knowledge_stats = (await db.execute(
        select(
            Question.knowledge_point,
            func.count(WrongQuestion.id).label('wrong_count')
        ).join(
            WrongQuestion, WrongQuestion.question_id == Question.id
        ).where(
            WrongQuestion.user_id == current_user.id
        ).group_by(Question.knowledge_point)
    )).all()

    knowledge_list = []
    for row in knowledge_stats:
        knowledge_list.append({
            'knowledge_point': row[0] or '未分类',
            'wrong_count': row[1]
        })

    # 最近7天错题趋势
    daily_stats = []
    for i in range(6, -1, -1):
        day_start = (datetime.now(timezone.utc) - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = (await db.execute(
            select(func.count(WrongQuestion.id)).where(
                WrongQuestion.user_id == current_user.id,
                WrongQuestion.last_wrong_at >= day_start,
                WrongQuestion.last_wrong_at < day_end
            )
        )).scalar() or 0
        daily_stats.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'wrong_count': count
        })

    return {
        'total_wrong': wrong_count,
        'today_wrong': today_wrong,
        'knowledge_stats': knowledge_list,
        'daily_trend': daily_stats,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'full_name': current_user.full_name
        }
    }


@router.get("/daily-question", summary="每日一题")
async def daily_question(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取每日一题（根据日期随机选择一道题）"""
    # 根据日期生成随机种子，保证同一天题目相同
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    seed = int(today.replace('-', '')) % 10000

    # 获取题目总数
    total = (await db.execute(select(func.count(Question.id)))).scalar() or 0
    if total == 0:
        return {'message': '题库为空'}

    # 随机偏移
    offset = seed % total
    result = await db.execute(
        select(Question).order_by(Question.id).offset(offset).limit(1)
    )
    question = result.scalar_one_or_none()

    if not question:
        return {'message': '暂无题目'}

    return {
        'date': today,
        'question': {
            'id': question.id,
            'question_code': question.question_code,
            'title': question.title,
            'content': question.content,
            'question_type': question.question_type,
            'difficulty': question.difficulty,
            'knowledge_point': question.knowledge_point,
            'options': question.options,
            # 不含答案，用户提交后才能看到
        }
    }


@router.get("/knowledge-points", summary="知识点列表")
async def knowledge_points(
    db: AsyncSession = Depends(get_db)
):
    """获取所有知识点列表（用于筛选），缓存5分钟"""
    # 先查缓存
    cache_key = "stats:knowledge_points"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Question.knowledge_point).distinct().where(
            Question.knowledge_point.isnot(None)
        )
    )
    points = [row[0] for row in result.all() if row[0]]
    result_data = {
        'items': sorted(points),
        'total': len(points)
    }

    # 写入缓存
    cache.set_json(cache_key, result_data, expire=300)
    return result_data


@router.get("/question-filters", summary="题目筛选选项")
async def question_filters(
    db: AsyncSession = Depends(get_db)
):
    """获取题目筛选选项（题型、难度、知识点），缓存5分钟"""
    cache_key = "stats:question_filters"
    cached = cache.get_json(cache_key)
    if cached:
        return cached

    # 题型
    types_result = await db.execute(
        select(Question.question_type).distinct().where(Question.question_type.isnot(None))
    )
    question_types = [row[0] for row in types_result.all() if row[0]]

    # 难度
    diff_result = await db.execute(
        select(Question.difficulty).distinct().where(Question.difficulty.isnot(None))
    )
    difficulties = [row[0] for row in diff_result.all() if row[0]]

    # 知识点
    kp_result = await db.execute(
        select(Question.knowledge_point).distinct().where(Question.knowledge_point.isnot(None))
    )
    knowledge_points = sorted([row[0] for row in kp_result.all() if row[0]])

    # 学段
    grade_result = await db.execute(
        select(Question.grade).distinct().where(Question.grade.isnot(None))
    )
    grades = [row[0] for row in grade_result.all() if row[0]]

    result_data = {
        'question_types': question_types,
        'difficulties': difficulties,
        'knowledge_points': knowledge_points,
        'grades': grades
    }

    cache.set_json(cache_key, result_data, expire=300)
    return result_data


@router.get("/rankings", summary="错题排行榜")
async def rankings(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取错题数量排行榜"""
    result = await db.execute(
        select(
            User.username,
            User.full_name,
            func.count(WrongQuestion.id).label('wrong_count')
        ).join(
            WrongQuestion, WrongQuestion.user_id == User.id
        ).group_by(User.id).order_by(func.count(WrongQuestion.id).desc()).limit(limit)
    )
    rankings = []
    for i, row in enumerate(result.all()):
        rankings.append({
            'rank': i + 1,
            'username': row[0],
            'full_name': row[1],
            'wrong_count': row[2]
        })

    # 当前用户排名
    my_rank = None
    my_wrong = (await db.execute(
        select(func.count(WrongQuestion.id)).where(WrongQuestion.user_id == current_user.id)
    )).scalar() or 0

    return {
        'rankings': rankings,
        'my_rank': my_rank,
        'my_wrong_count': my_wrong
    }
