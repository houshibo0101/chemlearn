"""
Pytest 配置 - 使用独立的测试数据库（不碰开发库 chemlearn.db）
"""
import sys
import os

# 把项目根目录加到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 必须在导入 app 之前指定：测试使用一次性数据库，由应用 lifespan 自动建表
_TEST_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_chemlearn.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ.setdefault("DEBUG", "true")

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import Base, AsyncSessionLocal, engine, init_db

_db_ready = False


async def _ensure_db():
    """ASGITransport 不触发 lifespan，需手动建表（仅一次）"""
    global _db_ready
    if not _db_ready:
        await init_db()
        _db_ready = True


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """创建测试客户端"""
    await _ensure_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    """创建数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session
