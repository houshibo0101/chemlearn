"""
站内通知 API：列表、未读数、标记已读
发布钩子通过 notify_users() 给班级学生发通知
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["通知"])


async def notify_users(db: AsyncSession, user_ids, title: str, content: str = "",
                       ntype: str = "system", related_id: int | None = None):
    """批量发送站内通知（自动去重），提交由本函数完成"""
    ids = {uid for uid in user_ids if uid}
    for uid in ids:
        db.add(Notification(
            user_id=uid, title=title[:250], content=content,
            ntype=ntype, related_id=related_id,
        ))
    if ids:
        await db.commit()


def _to_dict(n: Notification) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "ntype": n.ntype,
        "related_id": n.related_id,
        "is_read": bool(n.is_read),
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("", summary="我的通知列表")
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base = Notification.user_id == current_user.id
    total = (await db.execute(select(func.count(Notification.id)).where(base))).scalar()
    unread = (await db.execute(
        select(func.count(Notification.id)).where(base, Notification.is_read == False)  # noqa: E712
    )).scalar()
    query = (
        select(Notification)
        .where(base)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(query)).scalars().all()
    return {"total": total, "page": page, "page_size": page_size, "unread": unread, "items": [_to_dict(n) for n in items]}


@router.get("/unread-count", summary="未读通知数")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = (await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    )).scalar()
    return {"count": count}


@router.post("/read-all", summary="全部标记已读")
async def read_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "已全部标记为已读"}


@router.post("/{notification_id}/read", summary="标记单条已读")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    n = (await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not n:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="通知不存在")
    if not n.is_read:
        n.is_read = True
        await db.commit()
    return {"message": "已读"}
