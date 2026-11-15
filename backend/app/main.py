"""
化学学习助手 - FastAPI 主入口
"""
from contextlib import asynccontextmanager
import os
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
    offline_router, stats_router, admin_dashboard_router, admin_scores_router,
    question_import_router,
    open_platform_v2_router, knowledge_graph_router, question_ext_router,
    practice_records_router, notifications_router, papers_router, favorites_router, ai_tasks_router,
    matching_router,
    rankings_router,
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
        return admin


async def _matching_table_exists() -> bool:
    """连连看表是否已经存在（用来区分“新装/旧版升级”和“管理员删光了关卡”）"""
    from sqlalchemy import inspect
    from app.core.database import engine
    async with engine.connect() as conn:
        return await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).has_table("matching_sets"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    matching_was_there = await _matching_table_exists()
    await init_db()
    admin = await ensure_admin()
    if not matching_was_there and admin is not None:
        # 从旧版本升级（或首次建表）时补上示例关卡；管理员主动删空不会触发
        from app.services.matching_seed import seed_matching
        async with AsyncSessionLocal() as db:
            created = await seed_matching(db, admin.id)
        if created:
            print(f"[连连看] 已初始化 {created} 套示例关卡")
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
app.include_router(admin_scores_router, prefix=prefix)
app.include_router(question_import_router, prefix=prefix)
app.include_router(open_platform_v2_router, prefix=prefix)
app.include_router(knowledge_graph_router, prefix=prefix)
app.include_router(question_ext_router, prefix=prefix)
app.include_router(practice_records_router, prefix=prefix)
app.include_router(notifications_router, prefix=prefix)
app.include_router(papers_router, prefix=prefix)
app.include_router(favorites_router, prefix=prefix)
app.include_router(ai_tasks_router, prefix=prefix)
app.include_router(matching_router, prefix=prefix)
app.include_router(rankings_router, prefix=prefix)


@app.get("/", include_in_schema=False)
async def root():
    # 有官网静态页时返回官网；没有时保留原来的 API 信息，方便排查
    site_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site", "index.html")
    if os.path.exists(site_index):
        from fastapi.responses import FileResponse
        return FileResponse(site_index)
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


# ========== 隐藏管理员入口 ==========
_ADMIN_PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>管理后台登录</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
         font-family: 'Microsoft YaHei', system-ui, sans-serif;
         background: radial-gradient(circle at 20% 20%, #312e81, #0f172a 65%); color: #e2e8f0; }
  .card { width: min(420px, 92vw); background: rgba(15,23,42,.82); border: 1px solid rgba(148,163,184,.25);
          border-radius: 18px; padding: 32px 30px; box-shadow: 0 30px 80px rgba(0,0,0,.45); }
  h1 { margin: 0 0 6px; font-size: 22px; color: #fff; }
  .sub { margin: 0 0 24px; font-size: 13px; color: #94a3b8; }
  label { display: block; font-size: 13px; color: #cbd5e1; margin: 14px 0 6px; }
  input { width: 100%; padding: 12px 13px; border-radius: 10px; border: 1px solid #334155;
          background: #0f172a; color: #f8fafc; font-size: 14px; outline: none; }
  input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,.18); }
  button { width: 100%; margin-top: 22px; padding: 12px; border: 0; border-radius: 10px;
           background: #6366f1; color: #fff; font-size: 15px; font-weight: 600; cursor: pointer; }
  button:disabled { opacity: .6; cursor: wait; }
  #msg { min-height: 20px; margin-top: 14px; font-size: 13px; color: #fca5a5; text-align: center; }
  .foot { margin-top: 18px; font-size: 11px; color: #64748b; text-align: center; }
</style>
</head>
<body>
  <form class="card" id="loginForm">
    <h1>ChemLearn 管理后台</h1>
    <p class="sub">仅管理员可进入 · 请使用管理员账号登录</p>
    <label for="username">管理员账号</label>
    <input id="username" autocomplete="username" required>
    <label for="password">密码</label>
    <input id="password" type="password" autocomplete="current-password" required>
    <button id="submitBtn" type="submit">进入后台</button>
    <div id="msg"></div>
    <div class="foot">此入口不对外公开</div>
  </form>
<script>
(function () {
  var API = '/chem/api/v1';
  var DASH = '/chem/app/admin/dashboard';
  var form = document.getElementById('loginForm');
  var msg = document.getElementById('msg');
  var btn = document.getElementById('submitBtn');

  // 同一标签页已通过隐藏入口进入，可以直接进；否则必须重新验证
  if (sessionStorage.getItem('adminPortal') === '1' && localStorage.getItem('token')) {
    location.replace(DASH);
    return;
  }

  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    msg.textContent = '';
    var username = document.getElementById('username').value.trim();
    var password = document.getElementById('password').value;
    if (!username || !password) {
      msg.textContent = '请输入管理员账号和密码';
      return;
    }
    btn.disabled = true;
    btn.textContent = '验证中…';
    try {
      var resp = await fetch(API + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username, password: password }),
      });
      var data = await resp.json().catch(function () { return {}; });
      if (!resp.ok) {
        msg.textContent = data.detail || '登录失败';
        return;
      }
      if (!data.user || data.user.role !== 'admin') {
        msg.textContent = '该账号不是管理员，无法进入后台';
        return;
      }
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      sessionStorage.setItem('adminPortal', '1');
      location.replace(DASH);
    } catch (e) {
      msg.textContent = '网络错误，请稍后重试';
    } finally {
      btn.disabled = false;
      btn.textContent = '进入后台';
    }
  });
})();
</script>
</body>
</html>
"""


@app.get("/admin/T", include_in_schema=False)
@app.get("/admin/T/", include_in_schema=False)
async def admin_portal():
    return HTMLResponse(_ADMIN_PORTAL_HTML, headers={"X-Robots-Tag": "noindex, nofollow"})


# ========== 静态文件挂载（官网 + 前端页面 + 上传文件） ==========
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
import os

_site_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
_site_index = os.path.join(_site_dir, "index.html")
_site_assets = os.path.join(_site_dir, "assets")

if os.path.isdir(_site_assets):
    app.mount("/assets", StaticFiles(directory=_site_assets), name="site-assets")
    print(f"[静态文件] 官网资源已挂载: {_site_assets}")


_frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "web", "dist", "app")
_frontend_dir = os.path.normpath(_frontend_dir)
_uploads_dir = os.environ.get("UPLOAD_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
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
