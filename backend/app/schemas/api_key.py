"""
API Key 相关 Schema
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class APIKeyCreate(BaseModel):
    name: str
    scope: Optional[str] = "all"
    expires_at: Optional[datetime] = None


class APIKeyOut(BaseModel):
    """API Key列表输出（不显示完整key）"""
    id: int
    name: str
    key_prefix: str  # 只显示前8位
    scope: str = "all"
    is_active: bool
    call_count: int
    daily_limit: int = 1000
    rate_limit_per_minute: int = 60
    daily_call_count: int = 0
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyCreateOut(BaseModel):
    """创建API Key时返回完整key（仅创建时可见）"""
    id: int
    name: str
    key: str  # 完整key，仅创建时返回
    scope: str = "all"
    is_active: bool
    daily_limit: int = 1000
    rate_limit_per_minute: int = 60
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyLimitUpdate(BaseModel):
    """管理员修改API Key限额"""
    daily_limit: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    is_active: Optional[bool] = None


def api_key_to_out(key_obj) -> dict:
    """把APIKey模型转换成APIKeyOut字典（隐藏完整key）"""
    key = key_obj.key or ""
    # 显示时按天重置今日调用数（数据库只在调用时更新，这里做显示层处理）
    today = datetime.now().date()
    last_call = getattr(key_obj, "last_call_date", None)
    daily_calls = getattr(key_obj, "daily_call_count", 0) or 0
    if last_call and last_call != today:
        daily_calls = 0
    return {
        "id": key_obj.id,
        "name": key_obj.name,
        "key_prefix": key[:8] + "..." if len(key) > 8 else key,
        "scope": key_obj.scope or "all",
        "is_active": key_obj.is_active,
        "call_count": key_obj.call_count or 0,
        "daily_limit": getattr(key_obj, "daily_limit", 1000) or 1000,
        "rate_limit_per_minute": getattr(key_obj, "rate_limit_per_minute", 60) or 60,
        "daily_call_count": daily_calls,
        "created_at": key_obj.created_at,
        "expires_at": key_obj.expires_at,
    }
