# -*- coding: utf-8 -*-
"""
后台 AI 任务 API

POST /ai-tasks            创建任务（立即返回，后台执行，完成后发通知）
GET  /ai-tasks/{id}       查单个任务（前端轮询用）
GET  /ai-tasks            我的任务列表（最近 20 条）

task_type: explain（错题AI讲解）/ variant（AI变式题）
"""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import AITask, User
from app.services import ai_task_service

router = APIRouter(prefix="/ai-tasks", tags=["后台AI任务"])


class TaskCreate(BaseModel):
    task_type: str = Field(..., description="explain / variant")
    wrong_question_id: int
    follow_up: str | None = Field(None, max_length=500)
    count: int = Field(3, ge=1, le=5)


def _brief(t: AITask) -> dict:
    return {
        "id": t.id,
        "task_type": t.task_type,
        "status": t.status,
        "ref_id": t.ref_id,
        "error": t.error,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "finished_at": t.finished_at.isoformat() if t.finished_at else None,
        # 列表里不带 result，避免 payload 过大；详情里才给
        "has_result": bool(t.result),
    }


@router.post("", summary="创建后台 AI 任务")
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.task_type not in ("explain", "variant"):
        raise HTTPException(status_code=400, detail="task_type 只能是 explain 或 variant")

    task = AITask(
        user_id=current_user.id,
        task_type=data.task_type,
        ref_id=data.wrong_question_id,
        payload={"follow_up": data.follow_up, "count": data.count},
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 后台执行：不阻塞请求，完成后写通知
    asyncio.create_task(ai_task_service.run_task(task.id))
    return {"task_id": task.id, "status": "pending", "message": "已提交后台生成，完成后会通知你"}


@router.get("/{task_id}", summary="查询任务状态与结果")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(AITask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="无权查看该任务")

    out = _brief(task)
    out["result"] = task.result
    return out


@router.get("", summary="我的 AI 任务列表")
async def my_tasks(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(AITask)
        .where(AITask.user_id == current_user.id)
        .order_by(desc(AITask.created_at))
        .limit(min(50, max(1, limit)))
    )).scalars().all()
    return {"items": [_brief(t) for t in rows], "total": len(rows)}
