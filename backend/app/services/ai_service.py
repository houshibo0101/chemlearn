"""
AI 问答服务（OpenAI 兼容接口）
- 对话历史持久化
- 每用户 1MB 配额，超出后 FIFO 淘汰最早记录
- 总存储配额 5GB，超出后告警
- 记录每次 AI 调用的 token 消耗
"""
import httpx
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models import ChatHistory, AIUsage
from app.schemas.ai import ChatMessage

# 每用户对话历史配额：1MB
MAX_HISTORY_BYTES = 1 * 1024 * 1024
# 系统总存储配额：5GB
MAX_TOTAL_STORAGE_BYTES = 5 * 1024 * 1024 * 1024
# 加载给AI的最近历史条数
MAX_HISTORY_MESSAGES = 20


SYSTEM_PROMPT = r"""你是一位专业的高中化学老师，名叫"化学助手"。
你的职责是帮助高中生学习化学，包括：
1. 解答化学概念、原理、方程式等问题
2. 讲解题目解题思路和方法
3. 用通俗易懂的语言解释复杂概念
4. 鼓励学生思考，引导式教学

回答要求：
- 语言简洁明了，适合高中生理解
- 涉及化学方程式时，必须用 $...$ 包裹LaTeX公式，例如：$\text{Zn} + \text{H}_2\text{SO}_4 \rightarrow \text{ZnSO}_4 + \text{H}_2 \uparrow$
- 复杂公式单独一行用 $$...$$ 包裹
- 计算题要写出步骤
- 不要直接给出选择题答案，而是讲解知识点和解题思路
"""


class AIError(Exception):
    """AI 上游调用失败（携带上游错误详情，便于透传给前端诊断）"""
    pass


def _byte_size(text: str) -> int:
    """计算字符串的 UTF-8 字节大小"""
    return len(text.encode("utf-8"))


def _explain_model() -> str:
    """解析类任务（错题讲解等）使用的模型：AI_EXPLAIN_MODEL 优先，留空则回退 AI_MODEL"""
    return getattr(settings, "AI_EXPLAIN_MODEL", "") or settings.AI_MODEL


class AIService:
    # ========== 对话历史管理 ==========

    @staticmethod
    async def save_message(db: AsyncSession, user_id: int, role: str, content: str) -> ChatHistory:
        """保存一条对话记录"""
        msg = ChatHistory(
            user_id=user_id,
            role=role,
            content=content,
            content_size=_byte_size(content),
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def load_history(db: AsyncSession, user_id: int, limit: int = MAX_HISTORY_MESSAGES) -> List[ChatMessage]:
        """加载最近的历史对话（按时间正序返回，方便传给AI）"""
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.desc())
            .limit(limit)
        )
        items = result.scalars().all()
        # 倒序查出来的，反转成正序
        items.reverse()
        return [ChatMessage(role=item.role, content=item.content) for item in items]

    @staticmethod
    async def get_history_list(db: AsyncSession, user_id: int, limit: int = 100) -> List[ChatHistory]:
        """获取历史对话列表（正序，用于前端展示）"""
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.asc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def enforce_quota(db: AsyncSession, user_id: int, max_bytes: int = MAX_HISTORY_BYTES):
        """
        配额管理：如果该用户对话总大小超过 max_bytes，从最早的记录开始删除，直到低于阈值。
        实现 FIFO 环形覆盖。
        """
        total = (await db.execute(
            select(func.coalesce(func.sum(ChatHistory.content_size), 0))
            .where(ChatHistory.user_id == user_id)
        )).scalar()

        if total <= max_bytes:
            return 0

        deleted = 0
        # 从最早的记录开始删
        result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.id.asc())
        )
        records = result.scalars().all()

        current_total = total
        for record in records:
            if current_total <= max_bytes:
                break
            current_total -= record.content_size
            await db.delete(record)
            deleted += 1

        if deleted > 0:
            await db.commit()
        return deleted

    @staticmethod
    async def clear_history(db: AsyncSession, user_id: int) -> int:
        """清空该用户的所有对话历史，返回删除条数"""
        result = await db.execute(select(ChatHistory).where(ChatHistory.user_id == user_id))
        records = result.scalars().all()
        count = len(records)
        for r in records:
            await db.delete(r)
        await db.commit()
        return count

    @staticmethod
    async def get_history_size(db: AsyncSession, user_id: int) -> dict:
        """获取该用户对话历史的统计信息"""
        total_bytes = (await db.execute(
            select(func.coalesce(func.sum(ChatHistory.content_size), 0))
            .where(ChatHistory.user_id == user_id)
        )).scalar()
        total_count = (await db.execute(
            select(func.count(ChatHistory.id))
            .where(ChatHistory.user_id == user_id)
        )).scalar()
        return {
            "total_bytes": total_bytes,
            "total_count": total_count,
            "max_bytes": MAX_HISTORY_BYTES,
            "usage_percent": round(total_bytes / MAX_HISTORY_BYTES * 100, 2),
        }

    # ========== 系统统计 ==========

    @staticmethod
    async def get_total_storage(db: AsyncSession) -> dict:
        """获取系统总存储使用情况"""
        total_bytes = (await db.execute(
            select(func.coalesce(func.sum(ChatHistory.content_size), 0))
        )).scalar()
        total_count = (await db.execute(
            select(func.count(ChatHistory.id))
        )).scalar()
        user_count = (await db.execute(
            select(func.count(func.distinct(ChatHistory.user_id)))
        )).scalar()
        return {
            "total_bytes": total_bytes,
            "total_count": total_count,
            "user_count": user_count,
            "max_bytes": MAX_TOTAL_STORAGE_BYTES,
            "usage_percent": round(total_bytes / MAX_TOTAL_STORAGE_BYTES * 100, 2),
            "is_full": total_bytes >= MAX_TOTAL_STORAGE_BYTES,
            "warning": total_bytes >= MAX_TOTAL_STORAGE_BYTES * 0.9,
        }

    @staticmethod
    async def get_token_usage(db: AsyncSession, user_id: int = None) -> dict:
        """获取 token 消耗统计"""
        query = select(
            func.coalesce(func.sum(AIUsage.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(AIUsage.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(AIUsage.total_tokens), 0).label("total_tokens"),
            func.count(AIUsage.id).label("call_count"),
        )
        if user_id:
            query = query.where(AIUsage.user_id == user_id)
        result = (await db.execute(query)).first()
        return {
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "call_count": result.call_count,
        }

    # ========== AI 对话 ==========

    @staticmethod
    async def chat(
        message: str,
        history: Optional[List[ChatMessage]] = None,
        context: Optional[str] = None,
        raise_on_error: bool = True,
        model: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """
        返回 (回复内容, token使用信息)。
        model 不传则用 settings.AI_MODEL（问答/生成类）；解析类任务由调用方传 AI_EXPLAIN_MODEL。
        raise_on_error=True：调用失败抛 AIError（供程序化调用方捕获后明确报错，
        避免错误文案被当作 AI 回复去解析导致误导性的"JSON解析失败"）；
        raise_on_error=False：保持旧行为，把可读的错误文案作为回复返回（聊天页展示用）。
        """
        if not settings.AI_API_KEY:
            msg = "【AI 服务未配置】请在后端 .env 中设置 AI_API_KEY 和 AI_API_BASE。\n\n当前问题：" + message
            if raise_on_error:
                raise AIError("AI 服务未配置（缺少 AI_API_KEY）")
            return msg, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        used_model = model or settings.AI_MODEL

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": f"参考上下文：\n{context}"})
        if history:
            for h in history:
                messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": message})

        def _fail(e: Exception) -> Tuple[str, dict]:
            """提取上游错误详情（含响应体），返回错误文案"""
            detail = str(e)
            body = ""
            if isinstance(e, httpx.HTTPStatusError):
                try:
                    body = e.response.text[:500]
                except Exception:
                    pass
                detail = f"HTTP {e.response.status_code}"
                if body:
                    detail += f": {body}"
            err_msg = f"AI 服务调用失败：{detail}"
            if raise_on_error:
                raise AIError(err_msg) from e
            return err_msg, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.AI_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.AI_API_KEY}"},
                    json={
                        "model": used_model,
                        "messages": messages,
                        "temperature": 0.7,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                token_info = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
                return reply, token_info
        except httpx.TimeoutException:
            msg = "AI 服务响应超时，请稍后重试。"
            if raise_on_error:
                raise AIError(msg)
            return msg, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        except Exception as e:
            return _fail(e)

    @staticmethod
    async def chat_with_history(
        db: AsyncSession,
        user_id: int,
        message: str,
        context: Optional[str] = None,
    ) -> str:
        """
        带历史记录的 AI 对话：
        1. 加载最近历史
        2. 调用 AI
        3. 保存用户消息和 AI 回复
        4. 执行配额淘汰（每用户1MB）
        5. 记录 token 消耗
        """
        # 加载历史
        history = await AIService.load_history(db, user_id)

        # 调用 AI
        reply, token_info = await AIService.chat(message=message, history=history, context=context)

        # 保存用户消息
        await AIService.save_message(db, user_id, "user", message)
        # 保存 AI 回复
        await AIService.save_message(db, user_id, "assistant", reply)

        # 配额管理：超过 1MB 则删除最早的记录
        await AIService.enforce_quota(db, user_id)

        # 记录 token 消耗
        usage = AIUsage(
            user_id=user_id,
            model=settings.AI_MODEL,
            prompt_tokens=token_info["prompt_tokens"],
            completion_tokens=token_info["completion_tokens"],
            total_tokens=token_info["total_tokens"],
            usage_type="chat",
        )
        db.add(usage)
        await db.commit()

        return reply

    @staticmethod
    async def explain_wrong_question(
        db: AsyncSession,
        user_id: int,
        question_title: str,
        question_content: Optional[str],
        correct_answer: str,
        analysis: Optional[str],
        user_answer: Optional[str],
        follow_up: Optional[str] = None,
    ) -> str:
        """错题 AI 讲解 / 追问（不保存到对话历史，但记录token）"""
        context_parts = [f"题目：{question_title}"]
        if question_content:
            context_parts.append(f"题目详情：{question_content}")
        context_parts.append(f"正确答案：{correct_answer}")
        if analysis:
            context_parts.append(f"参考解析：{analysis}")
        if user_answer:
            context_parts.append(f"学生的错误答案：{user_answer}")

        if follow_up:
            message = follow_up
        else:
            message = "请详细讲解这道题的解题思路，分析学生错误的原因，并给出相关知识点总结。"

        reply, token_info = await AIService.chat(
            message=message, context="\n".join(context_parts), model=_explain_model()
        )

        # 记录 token 消耗
        usage = AIUsage(
            user_id=user_id,
            model=_explain_model(),
            prompt_tokens=token_info["prompt_tokens"],
            completion_tokens=token_info["completion_tokens"],
            total_tokens=token_info["total_tokens"],
            usage_type="wrong_explain",
        )
        db.add(usage)
        await db.commit()

        return reply
