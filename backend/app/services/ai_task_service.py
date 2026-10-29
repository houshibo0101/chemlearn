# -*- coding: utf-8 -*-
"""后台 AI 任务执行器：讲解 / 变式题"""
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import AITask, Notification, Question, WrongQuestion
from app.services.ai_service import AIService


async def _notify(db: AsyncSession, task: AITask, title: str, content: str) -> None:
    db.add(Notification(
        user_id=task.user_id,
        title=title,
        content=content,
        ntype="system",
        related_id=task.id,
    ))
    task.notified = True


async def _do_explain(db: AsyncSession, task: AITask) -> dict:
    """错题 AI 讲解（含追问）"""
    wq = (await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == task.ref_id)
    )).scalar_one_or_none()
    if not wq:
        raise RuntimeError("错题记录不存在")
    question = await db.get(Question, wq.question_id)
    if not question:
        raise RuntimeError("关联题目不存在")

    follow_up = (task.payload or {}).get("follow_up") or None
    reply = await AIService.explain_wrong_question(
        db=db,
        user_id=task.user_id,
        question_title=question.title,
        question_content=question.content,
        correct_answer=question.answer,
        analysis=question.analysis,
        user_answer=wq.user_answer,
        follow_up=follow_up,
    )

    user_msg = follow_up if follow_up else f"【错题讲解】{question.title}"
    await AIService.save_message(db, task.user_id, "user", user_msg)
    await AIService.save_message(db, task.user_id, "assistant", reply)
    await AIService.enforce_quota(db, task.user_id)

    return {"type": "explain", "reply": reply, "question_title": question.title}


VARIANTS_PROMPT = """请根据下面这道化学题，生成 {count} 道类似的变式题。

原题：
- 题型：{qtype}
- 难度：{difficulty}
- 知识点：{kp}
- 题干：{title}
{content}
- 选项：{options}
- 正确答案：{answer}
- 解析：{analysis}

要求：
1. 变式题考察相同知识点，但改变数据、情境或问法，不要和原题一样
2. 难度与原题相当
3. 选择题的 answer 必须是 options 中存在的选项 key；填空/计算题 options 给空数组 []
4. 严格只输出 JSON 数组，不要任何其他文字或 markdown 标记

JSON格式：
[{{"title":"题干","question_type":"single","difficulty":"medium","options":[{{"key":"A","text":"..."}}],"answer":"A","analysis":"解析"}}]"""


async def _do_variant(db: AsyncSession, task: AITask) -> dict:
    """AI 变式题（举一反三）"""
    wq = (await db.execute(
        select(WrongQuestion).where(WrongQuestion.id == task.ref_id)
    )).scalar_one_or_none()
    if not wq:
        raise RuntimeError("错题记录不存在")
    question = await db.get(Question, wq.question_id)
    if not question:
        raise RuntimeError("关联题目不存在")

    count = max(1, min(5, int((task.payload or {}).get("count") or 3)))
    prompt = VARIANTS_PROMPT.format(
        count=count,
        qtype=question.question_type.value if hasattr(question.question_type, "value") else question.question_type,
        difficulty=question.difficulty.value if hasattr(question.difficulty, "value") else question.difficulty,
        kp=question.knowledge_point or "未标注",
        title=question.title,
        content=question.content or "",
        options=question.options or "无（填空/计算/简答题）",
        answer=question.answer,
        analysis=question.analysis or "无",
    )

    reply, _ = await AIService.chat(prompt)
    content = reply.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()
    start, end = content.find("["), content.rfind("]") + 1
    if start < 0 or end <= start:
        raise RuntimeError("AI 返回格式异常，请重试")
    raw = json.loads(content[start:end])

    variants = []
    for v in raw if isinstance(raw, list) else []:
        if not isinstance(v, dict) or not v.get("title"):
            continue
        variants.append({
            "title": str(v.get("title"))[:800],
            "question_type": v.get("question_type", "single"),
            "difficulty": v.get("difficulty", "medium"),
            "options": v.get("options") or [],
            "answer": str(v.get("answer", "")),
            "analysis": str(v.get("analysis", "")),
        })
    if not variants:
        raise RuntimeError("AI 没有生成有效的变式题，请重试")

    return {
        "type": "variant",
        "original": {"id": question.id, "title": question.title,
                     "knowledge_point": question.knowledge_point},
        "count": len(variants),
        "variants": variants,
    }


async def run_task(task_id: int) -> None:
    """后台执行入口：自己开 session，失败也要把状态写回去"""
    async with AsyncSessionLocal() as db:
        task = await db.get(AITask, task_id)
        if not task or task.status in ("done", "running"):
            return
        task.status = "running"
        await db.commit()

        try:
            if task.task_type == "explain":
                result = await _do_explain(db, task)
                title, content = "AI 讲解已生成", "点击查看这道题的讲解内容"
            elif task.task_type == "variant":
                result = await _do_variant(db, task)
                n = result.get("count", 0)
                title, content = f"{n} 道变式题已生成", "举一反三练习已就绪，点击查看"
            else:
                raise RuntimeError(f"未知任务类型：{task.task_type}")

            task.result = result
            task.status = "done"
            task.finished_at = datetime.now(timezone.utc)
            await _notify(db, task, title, content)
            await db.commit()
            print(f"[AI任务] #{task.id} {task.task_type} 完成")
        except Exception as e:  # noqa: BLE001
            task.status = "failed"
            task.error = str(e)[:800]
            task.finished_at = datetime.now(timezone.utc)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
            print(f"[AI任务] #{task.id} {task.task_type} 失败：{e}")
