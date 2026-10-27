"""
离线模式路由：离线账户注册、绑定、错题同步、题目批量下载
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models import User, UserRole, WrongQuestion, OfflineBind, Question

router = APIRouter(prefix="/offline", tags=["离线模式"])

MAX_OFFLINE_CHILDREN = 2  # 每个正常账户最多绑定2个离线账户


# ========== 请求模型 ==========
class OfflineRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = None


class OfflineBindRequest(BaseModel):
    offline_username: str


class WrongQuestionItem(BaseModel):
    question_id: int
    user_answer: Optional[str] = None
    wrong_count: int = 1


class WrongQuestionBatchRequest(BaseModel):
    items: List[WrongQuestionItem]


# ========== 接口 ==========
@router.post("/register", summary="离线账户注册（免验证码）")
async def offline_register(data: OfflineRegisterRequest, db: AsyncSession = Depends(get_db)):
    """离线设备上注册账户，不需要邮箱验证码"""
    # 检查用户名
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=data.username,
        email=None,
        hashed_password=hash_password(data.password),
        full_name=data.full_name or data.username,
        grade=None,
        role=UserRole.STUDENT,
        tag="offline",  # 标记为离线账户
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), {"role": user.role.value})
    return {
        "success": True,
        "user_id": user.id,
        "username": user.username,
        "access_token": token,
        "message": "离线账户注册成功"
    }


@router.post("/bind", summary="绑定离线账户到正常账户")
async def bind_offline_account(
    data: OfflineBindRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """将离线账户绑定到当前正常账户，每个正常账户最多绑定2个"""
    # 查找离线账户
    result = await db.execute(select(User).where(User.username == data.offline_username))
    offline_user = result.scalar_one_or_none()
    if not offline_user:
        raise HTTPException(status_code=404, detail="离线账户不存在")

    # 检查是否已经绑定
    result = await db.execute(
        select(OfflineBind).where(
            OfflineBind.parent_user_id == current_user.id,
            OfflineBind.offline_user_id == offline_user.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该离线账户已绑定")

    # 检查绑定数量
    result = await db.execute(
        select(func.count(OfflineBind.id)).where(OfflineBind.parent_user_id == current_user.id)
    )
    count = result.scalar() or 0
    if count >= MAX_OFFLINE_CHILDREN:
        raise HTTPException(status_code=400, detail=f"最多只能绑定{MAX_OFFLINE_CHILDREN}个离线账户")

    # 创建绑定
    bind = OfflineBind(
        parent_user_id=current_user.id,
        offline_user_id=offline_user.id
    )
    db.add(bind)
    await db.commit()

    return {
        "success": True,
        "message": f"离线账户 {offline_user.username} 已绑定到 {current_user.username}",
        "bound_count": count + 1,
        "max_count": MAX_OFFLINE_CHILDREN
    }


@router.get("/bind-list", summary="获取已绑定的离线账户列表")
async def get_bind_list(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfflineBind).where(OfflineBind.parent_user_id == current_user.id)
    )
    binds = result.scalars().all()
    items = []
    for bind in binds:
        result2 = await db.execute(select(User).where(User.id == bind.offline_user_id))
        offline_user = result2.scalar_one_or_none()
        if offline_user:
            items.append({
                "id": bind.id,
                "offline_user_id": offline_user.id,
                "offline_username": offline_user.username,
                "full_name": offline_user.full_name,
                "created_at": bind.created_at.isoformat() if bind.created_at else None
            })
    return {"items": items, "total": len(items), "max_count": MAX_OFFLINE_CHILDREN}


@router.delete("/unbind/{offline_user_id}", summary="解绑离线账户")
async def unbind_offline_account(
    offline_user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(OfflineBind).where(
            OfflineBind.parent_user_id == current_user.id,
            OfflineBind.offline_user_id == offline_user_id
        )
    )
    bind = result.scalar_one_or_none()
    if not bind:
        raise HTTPException(status_code=404, detail="绑定关系不存在")

    await db.delete(bind)
    await db.commit()
    return {"success": True, "message": "已解绑"}


@router.post("/wrong-questions", summary="批量上传错题")
async def upload_wrong_questions(
    data: WrongQuestionBatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """离线模式下批量上传错题，上传到当前正常账户"""
    uploaded = 0
    skipped = 0

    for item in data.items:
        # 检查题目是否存在
        result = await db.execute(select(Question).where(Question.id == item.question_id))
        question = result.scalar_one_or_none()
        if not question:
            skipped += 1
            continue

        # 检查是否已有错题记录
        result = await db.execute(
            select(WrongQuestion).where(
                WrongQuestion.user_id == current_user.id,
                WrongQuestion.question_id == item.question_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 更新错误次数
            existing.wrong_count += item.wrong_count
            existing.user_answer = item.user_answer
            uploaded += 1
        else:
            # 新建错题记录
            wq = WrongQuestion(
                user_id=current_user.id,
                question_id=item.question_id,
                wrong_count=item.wrong_count,
                user_answer=item.user_answer
            )
            db.add(wq)
            uploaded += 1

    await db.commit()

    return {
        "success": True,
        "uploaded": uploaded,
        "skipped": skipped,
        "total": len(data.items)
    }


@router.get("/questions", summary="批量下载题目（用于离线缓存）")
async def download_questions(
    page: int = 1,
    page_size: int = 50,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    knowledge_point: Optional[str] = None,
    exclude_images: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量下载题目，包含答案和解析，用于离线缓存"""
    query = select(Question)

    if question_type and question_type != "ALL":
        # 数据库存的是大写（SINGLE/EASY），SQLite 的 = 区分大小写，
        # 用 func.lower 双侧归一，兼容客户端传大写或小写
        query = query.where(func.lower(Question.question_type) == question_type.lower())
    if difficulty and difficulty != "ALL":
        query = query.where(func.lower(Question.difficulty) == difficulty.lower())
    if knowledge_point and knowledge_point != "ALL":
        query = query.where(Question.knowledge_point == knowledge_point)
    if exclude_images:
        # 排除带图题目（images 为 JSON 数组文本，NULL 或空串视为无图）
        query = query.where(Question.images.is_(None) | (Question.images == ''))

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # 分页
    query = query.order_by(Question.id).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    questions = result.scalars().all()

    items = []
    for q in questions:
        items.append({
            "id": q.id,
            "question_code": q.question_code,
            "title": q.title,
            "content": q.content,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "grade": q.grade,
            "knowledge_point": q.knowledge_point,
            "options": q.options,
            "answer": q.answer,
            "analysis": q.analysis,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total
    }
