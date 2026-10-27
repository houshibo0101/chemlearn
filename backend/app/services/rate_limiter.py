"""
简单内存限流器
"""
import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """基于内存的滑动窗口限流器"""

    def __init__(self):
        self._requests = defaultdict(list)
        self._lock = Lock()

    def allow(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        检查是否允许请求
        key: 限流标识（如IP、用户ID、邮箱）
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
        """
        now = time.time()
        with self._lock:
            # 清理过期记录
            self._requests[key] = [
                t for t in self._requests[key]
                if now - t < window_seconds
            ]
            if len(self._requests[key]) >= max_requests:
                return False
            self._requests[key].append(now)
            return True

    def reset(self, key: str):
        """重置某个key的计数"""
        with self._lock:
            self._requests.pop(key, None)

    def get_remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """获取剩余请求数"""
        now = time.time()
        with self._lock:
            self._requests[key] = [
                t for t in self._requests[key]
                if now - t < window_seconds
            ]
            return max(0, max_requests - len(self._requests[key]))


# 全局限流器实例
rate_limiter = RateLimiter()

# 登录失败记录
login_failures = defaultdict(list)
login_lock = Lock()


def check_login_failure(ip: str, username: str) -> tuple[bool, int]:
    """
    检查登录失败次数
    返回: (是否允许, 剩余尝试次数)
    规则: 同一IP+用户名 5分钟内最多5次失败，超过锁定15分钟
    """
    now = time.time()
    key = f"{ip}:{username}"
    with login_lock:
        # 清理5分钟前的记录
        login_failures[key] = [
            t for t in login_failures[key]
            if now - t < 300
        ]
        # 检查是否在锁定期（15分钟内有5次以上失败）
        recent = [t for t in login_failures[key] if now - t < 900]
        if len(recent) >= 5:
            # 计算锁定剩余时间
            oldest = min(recent)
            lock_remaining = int(900 - (now - oldest))
            return False, max(0, lock_remaining)
        return True, max(0, 5 - len(login_failures[key]))


def record_login_failure(ip: str, username: str):
    """记录登录失败"""
    now = time.time()
    key = f"{ip}:{username}"
    with login_lock:
        login_failures[key].append(now)


def reset_login_failure(ip: str, username: str):
    """登录成功后重置失败计数"""
    key = f"{ip}:{username}"
    with login_lock:
        login_failures.pop(key, None)
