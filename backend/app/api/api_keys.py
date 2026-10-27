"""
API 开放平台 - 密钥管理路由
"""
import secrets
import string
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, APIKey, APICallLog
from app.schemas import APIKeyCreate, APIKeyOut, APIKeyCreateOut
from app.schemas.api_key import api_key_to_out

router = APIRouter(prefix="/api-keys", tags=["API开放平台"])


@router.get("/call-logs", summary="获取我的调用日志")
async def get_call_logs(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的API调用日志"""
    # 先查用户的所有key id
    keys = (await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )).scalars().all()
    key_ids = [k.id for k in keys]
    if not key_ids:
        return {"total": 0, "items": []}

    # 查调用日志（通过user_id过滤，因为日志里存了user_id）
    count = (await db.execute(
        select(func.count(APICallLog.id)).where(APICallLog.user_id == current_user.id)
    )).scalar()

    logs = (await db.execute(
        select(APICallLog)
        .where(APICallLog.user_id == current_user.id)
        .order_by(APICallLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    return {
        "total": count,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": log.id,
                "endpoint": log.endpoint,
                "method": log.method,
                "ip": log.ip,
                "api_key": log.api_key,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    }


@router.post("", response_model=APIKeyCreateOut, summary="创建API Key")
async def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 限制每个用户最多5个API Key
    existing = (await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )).scalars().all()
    if len(existing) >= 5:
        raise HTTPException(status_code=400, detail="每个用户最多创建5个API Key")

    # 验证用户是否有权限创建该scope的Key（管理员不受限）
    requested_scope = data.scope or "all"
    if current_user.role != "admin":
        allowed = (current_user.allowed_api_scopes or "all,question,ai").split(",")
        if requested_scope not in allowed:
            raise HTTPException(status_code=403, detail=f"你没有权限创建{requested_scope}权限的Key，允许的权限：{', '.join(allowed)}")

    # 生成纯字母数字的API Key（避免特殊字符在代码引用时报错）
    alphabet = string.ascii_letters + string.digits
    key_str = "ck_" + ''.join(secrets.choice(alphabet) for _ in range(40))
    api_key = APIKey(
        name=data.name,
        key=key_str,
        user_id=current_user.id,
        scope=data.scope or "all",
        expires_at=data.expires_at,
        daily_limit=getattr(current_user, 'daily_limit', 1000) or 1000,
        rate_limit_per_minute=60,
        is_active=False,  # 默认待审核，管理员审核通过后才激活
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return APIKeyCreateOut.model_validate(api_key)


@router.get("", summary="获取我的API Key列表")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id).order_by(APIKey.created_at.desc())
    )
    items = result.scalars().all()
    return [api_key_to_out(i) for i in items]


@router.get("/{key_id}/reveal", summary="查看完整API Key")
async def reveal_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看完整的API Key（仅本人可查看）"""
    key_obj = (await db.execute(select(APIKey).where(APIKey.id == key_id))).scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key不存在")
    if key_obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    return {"id": key_obj.id, "name": key_obj.name, "key": key_obj.key}


@router.delete("/{key_id}", summary="删除API Key")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    key_obj = (await db.execute(select(APIKey).where(APIKey.id == key_id))).scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key不存在")
    if key_obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    await db.delete(key_obj)
    await db.commit()
    return {"message": "已删除"}


# ========== 管理员审核接口 ==========

@router.get("/admin/pending", summary="【管理员】获取待审核的API Key列表")
async def list_pending_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看所有待审核的API Key"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    result = await db.execute(
        select(APIKey)
        .where(APIKey.is_active == False)
        .order_by(APIKey.created_at.desc())
    )
    items = result.scalars().all()

    # 关联用户信息
    pending_list = []
    for key in items:
        user = (await db.execute(select(User).where(User.id == key.user_id))).scalar_one_or_none()
        pending_list.append({
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key[:16] + "..." if len(key.key) > 16 else key.key,
            "scope": key.scope,
            "user_id": key.user_id,
            "username": user.username if user else "未知",
            "full_name": user.full_name if user else "",
            "email": user.email if user else "",
            "created_at": key.created_at.isoformat() if key.created_at else None,
        })
    return {"total": len(pending_list), "items": pending_list}


@router.post("/admin/{key_id}/approve", summary="【管理员】审核通过API Key")
async def approve_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员审核通过API Key，激活后可调用API"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    key_obj = (await db.execute(select(APIKey).where(APIKey.id == key_id))).scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key不存在")

    key_obj.is_active = True
    await db.commit()
    return {"message": "已审核通过", "key_id": key_id, "is_active": True}


@router.post("/admin/{key_id}/reject", summary="【管理员】拒绝API Key申请")
async def reject_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员拒绝API Key申请（删除）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    key_obj = (await db.execute(select(APIKey).where(APIKey.id == key_id))).scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=404, detail="API Key不存在")

    await db.delete(key_obj)
    await db.commit()
    return {"message": "已拒绝申请", "key_id": key_id}


# ===== 管理员：账户管理 =====

@router.get("/admin/users", summary="管理员-获取所有用户API使用情况")
async def admin_get_users(
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员获取所有用户列表及API使用统计"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    count = (await db.execute(select(func.count(User.id)))).scalar()
    users = (await db.execute(
        select(User).order_by(User.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    result = []
    today = datetime.now().strftime('%Y-%m-%d')
    for u in users:
        # 查用户的所有Key
        keys = (await db.execute(
            select(APIKey).where(APIKey.user_id == u.id)
        )).scalars().all()
        key_count = len(keys)
        total_calls = sum(k.call_count or 0 for k in keys)
        daily_limit = getattr(u, 'daily_limit', 1000) or 1000  # 用户默认额度
        # 按天重置今日调用数
        daily_calls = sum(
            (k.daily_call_count or 0) if (k.last_call_date and k.last_call_date == today) else 0
            for k in keys
        )

        result.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "key_count": key_count,
            "total_calls": total_calls,
            "daily_calls": daily_calls,
            "daily_limit": daily_limit,
            "allowed_api_scopes": u.allowed_api_scopes or "all,question,ai",
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"total": count, "page": page, "page_size": page_size, "items": result}


@router.post("/admin/users/{user_id}/quota", summary="管理员-修改用户API额度")
async def admin_update_quota(
    user_id: int,
    daily_limit: int,
    password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员修改用户API每日调用额度，需要验证管理员密码"""
    from app.core.security import verify_password

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    # 验证管理员密码
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="管理员密码错误")

    if daily_limit < 1 or daily_limit > 1000000:
        raise HTTPException(status_code=400, detail="额度范围：1-1000000")

    # 查找用户
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 修改用户默认额度（新创建的Key会用这个值）
    user.daily_limit = daily_limit

    # 修改该用户所有已有Key的额度
    keys = (await db.execute(
        select(APIKey).where(APIKey.user_id == user_id)
    )).scalars().all()

    for k in keys:
        k.daily_limit = daily_limit

    await db.commit()

    return {
        "message": f"已将用户 {user.username} 的API额度修改为 {daily_limit} 次/天",
        "user_id": user_id,
        "daily_limit": daily_limit,
        "updated_keys": len(keys),
    }


@router.post("/admin/users/{user_id}/scopes", summary="管理员-修改用户API权限范围")
async def admin_update_scopes(
    user_id: int,
    scopes: str,
    password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员修改用户允许创建的API Key权限范围，需要验证管理员密码
    scopes格式：逗号分隔，如 all,question,ai
    """
    from app.core.security import verify_password

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    # 验证管理员密码
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=403, detail="管理员密码错误")

    # 验证scopes格式
    valid_scopes = ["all", "question", "wrong", "ai", "class", "assignment", "exam", "admin"]
    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    for s in scope_list:
        if s not in valid_scopes:
            raise HTTPException(status_code=400, detail=f"无效的权限：{s}，可选：{', '.join(valid_scopes)}")
    if not scope_list:
        raise HTTPException(status_code=400, detail="至少选择一个权限")

    # 查找用户
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.allowed_api_scopes = ",".join(scope_list)
    await db.commit()

    return {
        "message": f"已将用户 {user.username} 的API权限修改为：{', '.join(scope_list)}",
        "user_id": user_id,
        "allowed_api_scopes": user.allowed_api_scopes,
    }


@router.get("/admin/call-logs", summary="管理员-查看全部API调用日志")
async def admin_get_call_logs(
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    ip: str | None = None,
    endpoint: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """管理员查看所有用户的API调用日志，支持按用户/IP/接口筛选"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可操作")

    query = select(APICallLog)
    count_query = select(func.count(APICallLog.id))

    if user_id:
        query = query.where(APICallLog.user_id == user_id)
        count_query = count_query.where(APICallLog.user_id == user_id)
    if ip:
        query = query.where(APICallLog.ip.like(f"%{ip}%"))
        count_query = count_query.where(APICallLog.ip.like(f"%{ip}%"))
    if endpoint:
        query = query.where(APICallLog.endpoint.like(f"%{endpoint}%"))
        count_query = count_query.where(APICallLog.endpoint.like(f"%{endpoint}%"))

    total = (await db.execute(count_query)).scalar()
    logs = (await db.execute(
        query.order_by(APICallLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()

    # 查用户名
    user_ids = list(set(log.user_id for log in logs))
    users = {}
    if user_ids:
        user_rows = (await db.execute(select(User.id, User.username).where(User.id.in_(user_ids)))).all()
        users = {row[0]: row[1] for row in user_rows}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": users.get(log.user_id, log.username or "未知"),
                "endpoint": log.endpoint,
                "method": log.method,
                "ip": log.ip,
                "api_key": log.api_key,
                "status_code": log.status_code,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
