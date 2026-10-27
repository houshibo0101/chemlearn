"""
AI 问答路由
- 支持本地AIService和远程AI服务两种模式
- 配置AI_SERVICE_URL则走远程调用（独立部署）
- 远程调用失败自动降级为本地或返回友好提示
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas import AIChatRequest, AIChatResponse, ChatMessageOut
from app.services import AIService
from app.services.rate_limiter import rate_limiter
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["AI问答"])

# 熔断器状态
_circuit_open = False
_circuit_fail_count = 0
_circuit_open_time = 0.0
_CIRCUIT_THRESHOLD = 5  # 连续失败5次熔断
_CIRCUIT_RESET_TIME = 30  # 30秒后尝试恢复


async def _call_ai_service(endpoint: str, payload: dict, timeout: int = 60):
    """调用远程AI服务，带熔断降级"""
    global _circuit_open, _circuit_fail_count, _circuit_open_time
    import time

    # 检查熔断是否到期恢复
    if _circuit_open and time.time() - _circuit_open_time > _CIRCUIT_RESET_TIME:
        _circuit_open = False
        _circuit_fail_count = 0
        print("[AI熔断] 熔断器已自动恢复")

    if _circuit_open:
        return None

    if not settings.AI_SERVICE_URL:
        return None  # 未配置远程服务，走本地

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{settings.AI_SERVICE_URL}{endpoint}",
                json=payload,
            )
            resp.raise_for_status()
            _circuit_fail_count = 0  # 成功重置计数
            return resp.json()
    except Exception as e:
        _circuit_fail_count += 1
        if _circuit_fail_count >= _CIRCUIT_THRESHOLD and not _circuit_open:
            _circuit_open = True
            _circuit_open_time = time.time()
            print(f"[AI熔断] 连续失败{_circuit_fail_count}次，熔断开启，{_CIRCUIT_RESET_TIME}秒后自动恢复")
        print(f"[AI远程调用失败] {endpoint}: {e}，降级到本地")
        return None


@router.post("/chat", response_model=AIChatResponse, summary="AI化学问答（自动保存历史）")
async def ai_chat(
    data: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 限流：每分钟10次
    if not rate_limiter.allow(f"ai_min_{current_user.id}", 10, 60):
        raise HTTPException(status_code=429, detail="AI问答调用过于频繁，每分钟最多10次")

    # 限流：每天100次
    if not rate_limiter.allow(f"ai_day_{current_user.id}", 100, 86400):
        raise HTTPException(status_code=429, detail="今日AI问答已达上限（100次）")

    # 尝试远程AI服务
    if data.history:
        # 前端传了历史，用纯对话接口
        result = await _call_ai_service("/chat", {
            "message": data.message,
            "history": [h.model_dump() for h in data.history] if data.history else None,
            "context": data.context,
        })
        if result:
            reply = result.get("reply", "")
            # 保存到数据库
            await AIService.save_message(db, current_user.id, "user", data.message)
            await AIService.save_message(db, current_user.id, "assistant", reply)
            await AIService.enforce_quota(db, current_user.id)
            return AIChatResponse(reply=reply, model=settings.AI_MODEL)
        # 降级到本地
        reply = await AIService.chat(
            message=data.message,
            history=data.history,
            context=data.context,
        )
        await AIService.save_message(db, current_user.id, "user", data.message)
        await AIService.save_message(db, current_user.id, "assistant", reply)
        await AIService.enforce_quota(db, current_user.id)
    else:
        # 用带历史的接口
        result = await _call_ai_service("/chat-with-history", {
            "user_id": current_user.id,
            "message": data.message,
            "context": data.context,
        })
        if result:
            reply = result.get("reply", "")
            return AIChatResponse(reply=reply, model=settings.AI_MODEL)
        # 降级到本地
        reply = await AIService.chat_with_history(
            db=db,
            user_id=current_user.id,
            message=data.message,
            context=data.context,
        )

    return AIChatResponse(reply=reply, model=settings.AI_MODEL)


@router.get("/history", summary="获取我的AI对话历史")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 尝试远程
    result = await _call_ai_service(f"/history/{current_user.id}", {}, timeout=10)
    if result is not None:
        return result
    # 降级本地
    items = await AIService.get_history_list(db, current_user.id)
    return [ChatMessageOut.model_validate(item) for item in items]


@router.delete("/history", summary="清空我的AI对话历史")
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await _call_ai_service(f"/history/{current_user.id}", {}, timeout=10)
    # 远程调用用DELETE，这里简化处理
    if settings.AI_SERVICE_URL and not _circuit_open:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.delete(f"{settings.AI_SERVICE_URL}/history/{current_user.id}")
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            print(f"[AI远程清空历史失败] {e}，降级本地")
    count = await AIService.clear_history(db, current_user.id)
    return {"message": f"已清空 {count} 条对话记录"}


@router.get("/history/stats", summary="获取对话历史配额使用情况")
async def history_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await _call_ai_service(f"/history/{current_user.id}/stats", {}, timeout=10)
    if result is not None:
        return result
    return await AIService.get_history_size(db, current_user.id)
