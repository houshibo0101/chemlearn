"""
缓存服务 - 支持Redis和内存缓存两种模式
如果配置了Redis地址则使用Redis，否则使用内存缓存
"""
import json
import time
from typing import Optional, Any
from app.core.config import settings

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class MemoryCache:
    """内存缓存（带过期时间）"""

    def __init__(self):
        self._cache = {}
        self._expire = {}

    def get(self, key: str) -> Optional[str]:
        if key in self._expire and time.time() > self._expire[key]:
            del self._cache[key]
            del self._expire[key]
            return None
        return self._cache.get(key)

    def set(self, key: str, value: str, expire: int = 300) -> bool:
        self._cache[key] = value
        self._expire[key] = time.time() + expire
        return True

    def delete(self, key: str) -> bool:
        self._cache.pop(key, None)
        self._expire.pop(key, None)
        return True

    def exists(self, key: str) -> bool:
        if key in self._expire and time.time() > self._expire[key]:
            del self._cache[key]
            del self._expire[key]
            return False
        return key in self._cache

    def incr(self, key: str, amount: int = 1) -> int:
        current = int(self.get(key) or 0)
        current += amount
        self.set(key, str(current), 86400)
        return current


class CacheService:
    """统一缓存服务"""

    def __init__(self):
        self._redis = None
        self._memory = MemoryCache()
        self._use_redis = False

        if REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self._redis.ping()
                self._use_redis = True
                print("[缓存] 使用Redis缓存")
            except Exception as e:
                print(f"[缓存] Redis连接失败，使用内存缓存: {e}")
                self._use_redis = False
        else:
            print("[缓存] 使用内存缓存（未配置Redis）")

    @property
    def is_redis(self) -> bool:
        return self._use_redis

    def get(self, key: str) -> Optional[str]:
        if self._use_redis:
            return self._redis.get(key)
        return self._memory.get(key)

    def set(self, key: str, value: str, expire: int = 300) -> bool:
        if self._use_redis:
            return self._redis.set(key, value, ex=expire)
        return self._memory.set(key, value, expire)

    def delete(self, key: str) -> bool:
        if self._use_redis:
            return self._redis.delete(key) > 0
        return self._memory.delete(key)

    def exists(self, key: str) -> bool:
        if self._use_redis:
            return self._redis.exists(key) > 0
        return self._memory.exists(key)

    def incr(self, key: str, amount: int = 1, expire: int = 86400) -> int:
        if self._use_redis:
            val = self._redis.incr(key, amount)
            if expire:
                self._redis.expire(key, expire)
            return val
        return self._memory.incr(key, amount)

    # 便捷方法：JSON序列化
    def get_json(self, key: str) -> Optional[Any]:
        val = self.get(key)
        if val:
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def set_json(self, key: str, value: Any, expire: int = 300) -> bool:
        return self.set(key, json.dumps(value, ensure_ascii=False, default=str), expire)

    # 按模式删除
    def delete_pattern(self, pattern: str) -> int:
        if self._use_redis:
            keys = self._redis.keys(pattern)
            if keys:
                return self._redis.delete(*keys)
            return 0
        # 内存缓存简单匹配
        count = 0
        for key in list(self._memory._cache.keys()):
            if pattern.replace('*', '') in key:
                self._memory.delete(key)
                count += 1
        return count


# 全局缓存实例
cache = CacheService()
