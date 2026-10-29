# -*- coding: utf-8 -*-
"""
题目收藏 API

前端契约（Favorites.vue / PracticeExam.vue 早就在调，之前后端没实现）：
  GET    /favorites                 分页列表
  GET    /favorites/question-ids    只要 id 数组（刷题页标记星标用）
  POST   /favorites/{question_id}   收藏
  DELETE /favorites/{question_id}   取消收藏
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import Favorite, Question, User

router = APIRouter(prefix="/favorites", tags=["题目收藏"])


def _brief(fav: Favorite, q: Question) -> dict:
    return {
        "id": fav.id,
        "question_id": fav.question_id,
        "created_at": fav.created_at.isoformat() if fav.created_at else None,
        "title": q.title,
        "content": q.content,
        "question_type": q.question_type.value if hasattr(q.question_type, "value") else q.question_type,
        "difficulty": q.difficulty.value if hasattr(q.difficulty, "value") else q.difficulty,
        "knowledge_point": q.knowledge_point,
        "grade": q.grade,
    }


@router.get("", summary="我的收藏列表")
async def list_favorites(
    page: int = 1,
    page_size: int = 20,
    knowledge_point: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    page = max(1, page)
    page_size = min(100, max(1, page_size))

    q = (
        select(Favorite, Question)
        .join(Question, Question.id == Favorite.question_id)
        .where(Favorite.user_id == current_user.id)
    )
    count_q = (
        select(func.count(Favorite.id))
        .join(Question, Question.id == Favorite.question_id)
        .where(Favorite.user_id == current_user.id)
    )
    if knowledge_point:
        q = q.where(Question.knowledge_point == knowledge_point)
        count_q = count_q.where(Question.knowledge_point == knowledge_point)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        q.order_by(desc(Favorite.created_at)).offset((page - 1) * page_size).limit(page_size)
    )).all()

    return {"items": [_brief(fav, ques) for fav, ques in rows], "total": total,
            "page": page, "page_size": page_size}


@router.get("/question-ids", summary="我收藏的题目 id（刷题页标星用）")
async def favorite_ids(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Favorite.question_id).where(Favorite.user_id == current_user.id)
    )).scalars().all()
    return list(rows)


@router.post("/{question_id}", summary="收藏题目")
async def add_favorite(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    existed = (await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.question_id == question_id,
        )
    )).scalar_one_or_none()
    if existed:
        return {"ok": True, "favorited": True, "message": "已经收藏过了"}

    db.add(Favorite(user_id=current_user.id, question_id=question_id))
    await db.commit()
    return {"ok": True, "favorited": True, "message": "已收藏"}


@router.delete("/{question_id}", summary="取消收藏")
async def remove_favorite(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fav = (await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.question_id == question_id,
        )
    )).scalar_one_or_none()
    if not fav:
        return {"ok": True, "favorited": False, "message": "本来就没收藏"}

    await db.delete(fav)
    await db.commit()
    return {"ok": True, "favorited": False, "message": "已取消收藏"}
