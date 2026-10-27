"""
化学学习助手 - FastAPI 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.core.database import init_db, AsyncSessionLocal
from app.core.security import hash_password
from app.models import User, UserRole
from app.api import (
    auth_router, questions_router, wrong_questions_router,
    ai_router, api_keys_router, open_platform_router, admin_users_router,
    classes_router, assignments_router, exams_router, teacher_router,
    offline_router, stats_router, admin_dashboard_router, question_import_router,
    open_platform_v2_router, knowledge_graph_router, question_ext_router,
    practice_records_router, notifications_router,
)


async def ensure_admin():
    """确保内置管理员账号存在"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.ADMIN_USERNAME))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                full_name="系统管理员",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            print(f"[初始化] 内置管理员账号已创建: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
        else:
            print(f"[初始化] 内置管理员账号已存在: {settings.ADMIN_USERNAME}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    await init_db()
    await ensure_admin()
    yield
    # 关闭


app = FastAPI(
    title=settings.APP_NAME,
    description="""## 📖 使用说明

高中化学学习助手 API - 多端协作平台，支持网页端、手机端、香橙派 Mini 端同时访问。

### 🔐 认证方式

**方式一：用户登录（Bearer Token）**
1. 调用 `POST /api/v1/auth/register` 注册账号
2. 调用 `POST /api/v1/auth/login` 登录，获取 `access_token`
3. 后续请求在 Header 中携带：`Authorization: Bearer <token>`

**方式二：开放平台 API Key**
1. 登录后调用 `POST /api/v1/api-keys` 创建 API Key
2. 调用开放接口时在 Header 中携带：`X-API-Key: <your_key>`
3. 开放接口前缀：`/api/v1/open/`

### 📚 功能模块

| 模块 | 前缀 | 说明 |
|------|------|------|
| 认证 | `/auth` | 注册、登录、个人信息管理 |
| 题目 | `/questions` | 刷题、提交答案、管理员题库管理 |
| 错题 | `/wrong-questions` | 错题记录、AI讲解、Excel导出 |
| AI问答 | `/ai` | 化学智能问答 |
| API密钥 | `/api-keys` | 开放平台密钥管理 |
| 开放平台 | `/open` | 对外公开接口（API Key鉴权） |
| 离线模式 | `/offline` | 离线账户注册、绑定、错题同步、题目批量下载 |
| 学习统计 | `/stats` | 学习概览、每日一题、知识点列表、排行榜 |

### ⚠️ 注意事项

- 学生账号只能刷题和查看自己的错题，管理员账号可管理题库
- 错题自动去重：同一用户同一题目只保留一条记录，错误次数累加
- 错题 Excel 导出包含：姓名、学段、错题题目、错误次数、最后错误时间
- AI 问答需在服务器 `.env` 中配置 `AI_API_KEY` 后方可使用
- 所有接口返回 JSON 格式，时间字段为 ISO 8601 格式

### 🔗 相关链接

- 前端应用：`/app/`
- ReDoc 文档：`/api/redoc`
- 健康检查：`/api/health`
""",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
prefix = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=prefix)
app.include_router(questions_router, prefix=prefix)
app.include_router(wrong_questions_router, prefix=prefix)
app.include_router(ai_router, prefix=prefix)
app.include_router(api_keys_router, prefix=prefix)
app.include_router(open_platform_router, prefix=prefix)
app.include_router(admin_users_router, prefix=prefix)
app.include_router(classes_router, prefix=prefix)
app.include_router(assignments_router, prefix=prefix)
app.include_router(exams_router, prefix=prefix)
app.include_router(teacher_router, prefix=prefix)
app.include_router(offline_router, prefix=prefix)
app.include_router(stats_router, prefix=prefix)
app.include_router(admin_dashboard_router, prefix=prefix)
app.include_router(question_import_router, prefix=prefix)
app.include_router(open_platform_v2_router, prefix=prefix)
app.include_router(knowledge_graph_router, prefix=prefix)
app.include_router(question_ext_router, prefix=prefix)
app.include_router(practice_records_router, prefix=prefix)
app.include_router(notifications_router, prefix=prefix)


@app.get("/", tags=["根"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "api_prefix": prefix,
        "admin_default": "admin / admin123",
    }


@app.get("/api/health", tags=["健康检查"])
async def health():
    """健康检查接口 - 检查服务状态和数据库连接"""
    import time
    import psutil
    from datetime import datetime, timezone

    start_time = time.time()

    # 检查数据库连接
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(select(1))
    except Exception as e:
        db_status = f"error: {str(e)}"

    # 系统资源
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        system_info = {
            "cpu_percent": cpu_percent,
            "memory_total_mb": round(memory.total / 1024 / 1024, 1),
            "memory_used_mb": round(memory.used / 1024 / 1024, 1),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
            "disk_percent": disk.percent,
        }
    except Exception:
        system_info = {"error": "psutil not available"}

    response_time_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "response_time_ms": response_time_ms,
        "version": "1.0.0",
        "system": system_info,
    }


# ========== 静态文件挂载（前端页面 + 上传文件） ==========
from fastapi.staticfiles import StaticFiles
import os

_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "web", "dist", "app")
_frontend_dir = os.path.normpath(_frontend_dir)
_uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
_uploads_dir = os.path.normpath(_uploads_dir)

from starlette.exceptions import HTTPException as _StarletteHTTPException


class SPAStaticFiles(StaticFiles):
    """SPA 静态文件服务：深链接/刷新子路径 404 时回退到 index.html"""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except _StarletteHTTPException as exc:
            if exc.status_code == 404 and "." not in os.path.basename(path):
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and "." not in os.path.basename(path):
            return await super().get_response("index.html", scope)
        return response


if os.path.exists(_frontend_dir):
    app.mount("/app", SPAStaticFiles(directory=_frontend_dir, html=True), name="app")
    print(f"[静态文件] 前端已挂载: {_frontend_dir}")
else:
    print(f"[静态文件] 警告: 前端目录不存在 {_frontend_dir}")

os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")
print(f"[静态文件] 上传目录已挂载: {_uploads_dir}")
# ========== 静态文件挂载结束 ==========
