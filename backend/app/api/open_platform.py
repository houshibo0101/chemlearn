"""
API 开放平台 - 对外公开接口（通过 X-API-Key 鉴权）
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models import User, Question, APIKey, APICallLog, ClassRoom
from app.schemas import QuestionPracticeOut
from app.services.rate_monitor import record_call, check_anomaly, mark_suspicious
from app.services.rate_limiter import rate_limiter
from datetime import datetime, timezone

router = APIRouter(prefix="/open", tags=["开放平台"])


def verify_api_key(required_scope: str = "all"):
    """验证API Key权限的依赖工厂"""
    async def _verify(
        request: Request,
        x_api_key: str = Header(..., alias="X-API-Key"),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        result = await db.execute(select(APIKey).where(APIKey.key == x_api_key, APIKey.is_active == True))
        key_obj = result.scalar_one_or_none()
        if not key_obj:
            # 检查是否存在但未审核
            pending = (await db.execute(select(APIKey).where(APIKey.key == x_api_key))).scalar_one_or_none()
            if pending and not pending.is_active:
                raise HTTPException(status_code=403, detail="API Key待管理员审核通过后才能使用")
            raise HTTPException(status_code=401, detail="无效的API Key")
        if key_obj.expires_at and key_obj.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="API Key已过期")

        # 验证权限范围
        scopes = (key_obj.scope or "all").split(",")
        if "all" not in scopes and required_scope not in scopes:
            scope_text = {
                "question": "题目查询", "ai": "AI问答", "wrong": "错题本",
                "class": "班级管理", "assignment": "作业管理", "exam": "考试管理", "admin": "管理员功能"
            }.get(required_scope, required_scope)
            raise HTTPException(status_code=403, detail=f"该API Key无{scope_text}权限")

        # 检查每分钟限流
        if key_obj.rate_limit_per_minute and key_obj.rate_limit_per_minute > 0:
            if not rate_limiter.allow(f"apikey_{key_obj.id}", key_obj.rate_limit_per_minute, 60):
                raise HTTPException(status_code=429, detail=f"调用过于频繁，每分钟最多{key_obj.rate_limit_per_minute}次")

        # 检查每日限额
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if key_obj.last_call_date != today:
            key_obj.daily_call_count = 0
            key_obj.last_call_date = today

        if key_obj.daily_limit and key_obj.daily_limit > 0:
            if key_obj.daily_call_count >= key_obj.daily_limit:
                raise HTTPException(status_code=429, detail=f"今日调用已达上限{key_obj.daily_limit}次")

        # 记录调用
        key_obj.call_count += 1
        key_obj.daily_call_count += 1
        user_id = key_obj.user_id
        record_call(user_id)

        # 记录调用日志
        try:
            client_ip = request.client.host if request.client else None
            log = APICallLog(
                user_id=user_id,
                username=None,  # 异步环境下避免懒加载，后续可单独查询
                endpoint=request.url.path,
                method=request.method,
                ip=client_ip,
                api_key=key_obj.key[:16] + "..." if len(key_obj.key) > 16 else key_obj.key,
            )
            db.add(log)
        except Exception as e:
            print(f"[日志] 记录调用失败: {e}")

        # 检查异常调用
        anomaly_result = check_anomaly(user_id)
        if anomaly_result["is_anomaly"]:
            reason = "; ".join(anomaly_result["details"]["anomalies"])
            await mark_suspicious(db, user_id, reason)

        await db.commit()

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="关联用户不存在")

        # 如果用户被封禁，拒绝访问
        if not user.is_active or user.tag == "banned":
            raise HTTPException(status_code=403, detail="账号已被封禁，请联系管理员")

        return user
    return _verify


@router.get("/questions", summary="【开放】获取题目列表")
async def open_list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    grade: str | None = None,
    difficulty: str | None = None,
    keyword: str | None = None,
    user: User = Depends(verify_api_key("question")),
    db: AsyncSession = Depends(get_db),
):
    query = select(Question)
    count_query = select(func.count(Question.id))
    if grade:
        query = query.where(Question.grade == grade)
        count_query = count_query.where(Question.grade == grade)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
        count_query = count_query.where(Question.difficulty == difficulty)
    if keyword:
        f = or_(Question.title.contains(keyword), Question.knowledge_point.contains(keyword))
        query = query.where(f)
        count_query = count_query.where(f)
    total = (await db.execute(count_query)).scalar()
    query = query.order_by(Question.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(query)).scalars().all()
    return {"total": total, "page": page, "page_size": page_size, "items": [QuestionPracticeOut.model_validate(i) for i in items]}


@router.get("/questions/{question_id}", summary="【开放】获取单题详情")
async def open_get_question(
    question_id: int,
    user: User = Depends(verify_api_key("question")),
    db: AsyncSession = Depends(get_db),
):
    q = (await db.execute(select(Question).where(Question.id == question_id))).scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="题目不存在")
    return QuestionPracticeOut.model_validate(q)


@router.get("/stats", summary="【开放】获取题库统计")
async def open_stats(
    db: AsyncSession = Depends(get_db),
):
    """公开接口，无需API Key，返回首页展示用统计数据"""
    total_questions = (await db.execute(select(func.count(Question.id)))).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    total_classes = (await db.execute(select(func.count(ClassRoom.id)))).scalar() or 0
    # 统计高考真题套数（不同的question_code前缀，如GK2024-XKB）
    paper_codes = (await db.execute(
        select(Question.question_code).where(Question.question_code.like("GK%"))
    )).scalars().all()
    paper_set = set()
    for code in paper_codes:
        if code and len(code) >= 10:
            paper_set.add(code[:10])
    gaokao_papers = len(paper_set)
    return {
        "total_questions": total_questions,
        "total_users": total_users,
        "total_classes": total_classes,
        "gaokao_papers": gaokao_papers,
    }


# ========== AI 问答接口 ==========

@router.post("/ai/chat", summary="【开放】AI问答")
async def open_ai_chat(
    request: dict,
    user: User = Depends(verify_api_key("ai")),
    db: AsyncSession = Depends(get_db),
):
    """调用AI问答接口
    请求体: {"message": "你的问题", "conversation_id": "可选，用于多轮对话"}
    """
    from app.services import AIService
    message = request.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="message不能为空")

    conversation_id = request.get("conversation_id")
    try:
        reply, usage = await AIService.chat(
            message=message,
        )
        return {
            "answer": reply,
            "conversation_id": conversation_id,
            "usage": usage,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI服务异常: {str(e)}")
