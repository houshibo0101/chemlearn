"""
API 调用频率监控服务
"""
import time
from collections import defaultdict
from typing import Dict, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, APICallLog

# 内存中的调用统计: {user_id: [timestamp1, timestamp2, ...]}
_call_timestamps: Dict[int, List[float]] = defaultdict(list)

# 频率阈值配置
RATE_LIMITS = {
    "per_minute": 120,      # 每分钟最多120次
    "per_hour": 3000,       # 每小时最多3000次
    "burst": 30,            # 10秒内最多30次（突发限制）
}


def record_call(user_id: int):
    """记录一次API调用"""
    now = time.time()
    _call_timestamps[user_id].append(now)
    # 清理超过1小时的记录
    _call_timestamps[user_id] = [t for t in _call_timestamps[user_id] if now - t < 3600]


def check_anomaly(user_id: int) -> dict:
    """检查用户调用是否异常，返回异常信息"""
    now = time.time()
    timestamps = _call_timestamps.get(user_id, [])
    if not timestamps:
        return {"is_anomaly": False, "details": {}}

    minute_count = len([t for t in timestamps if now - t < 60])
    hour_count = len([t for t in timestamps if now - t < 3600])
    burst_count = len([t for t in timestamps if now - t < 10])

    anomalies = []
    if minute_count > RATE_LIMITS["per_minute"]:
        anomalies.append(f"每分钟调用{minute_count}次，超过阈值{RATE_LIMITS['per_minute']}")
    if hour_count > RATE_LIMITS["per_hour"]:
        anomalies.append(f"每小时调用{hour_count}次，超过阈值{RATE_LIMITS['per_hour']}")
    if burst_count > RATE_LIMITS["burst"]:
        anomalies.append(f"10秒内突发调用{burst_count}次，超过阈值{RATE_LIMITS['burst']}")

    return {
        "is_anomaly": len(anomalies) > 0,
        "details": {
            "per_minute": minute_count,
            "per_hour": hour_count,
            "burst_10s": burst_count,
            "anomalies": anomalies,
        }
    }


async def mark_suspicious(db: AsyncSession, user_id: int, reason: str):
    """将用户标记为数据异常"""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user and user.tag == "normal":
        user.tag = "suspicious"
        await db.commit()
        print(f"[监控] 用户 {user.username} 被标记为数据异常: {reason}")


async def get_user_stats(db: AsyncSession, user_id: int) -> dict:
    """获取用户API调用统计"""
    now = time.time()
    timestamps = _call_timestamps.get(user_id, [])
    minute_count = len([t for t in timestamps if now - t < 60])
    hour_count = len([t for t in timestamps if now - t < 3600])

    # 从数据库获取总调用次数
    total = (await db.execute(
        select(func.count(APICallLog.id)).where(APICallLog.user_id == user_id)
    )).scalar() or 0

    return {
        "total_calls": total,
        "calls_per_minute": minute_count,
        "calls_per_hour": hour_count,
        "is_anomaly": check_anomaly(user_id)["is_anomaly"],
    }


async def get_suspicious_users(db: AsyncSession) -> list:
    """获取所有被标记为数据异常的用户"""
    users = (await db.execute(
        select(User).where(User.tag == "suspicious").order_by(User.id)
    )).scalars().all()
    return users


def cleanup_old_records():
    """清理过期的调用记录"""
    now = time.time()
    for user_id in list(_call_timestamps.keys()):
        _call_timestamps[user_id] = [t for t in _call_timestamps[user_id] if now - t < 3600]
        if not _call_timestamps[user_id]:
            del _call_timestamps[user_id]
