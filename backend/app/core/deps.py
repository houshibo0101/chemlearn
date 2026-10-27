"""
认证依赖：获取当前用户、管理员校验
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User, UserRole, APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


async def get_current_teacher_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.TEACHER]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要老师或管理员权限")
    return current_user


async def get_api_key_user(
    api_key: str,
    db: AsyncSession,
) -> User | None:
    """通过 API Key 鉴权（开放平台用）"""
    result = await db.execute(select(APIKey).where(APIKey.key == api_key, APIKey.is_active == True))
    key_obj = result.scalar_one_or_none()
    if not key_obj:
        return None
    if key_obj.expires_at and key_obj.expires_at < datetime.now(timezone.utc):
        return None
    key_obj.call_count += 1
    await db.commit()
    result = await db.execute(select(User).where(User.id == key_obj.user_id))
    return result.scalar_one_or_none()


from datetime import datetime, timezone  # noqa
