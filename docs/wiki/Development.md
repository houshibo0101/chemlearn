# 开发指南

---

## 目录结构

```
chemlearn/
├── backend/
│   ├── app/
│   │   ├── api/           24 个路由模块
│   │   ├── models/        17 张表
│   │   ├── schemas/       Pydantic 出入参
│   │   ├── services/      业务逻辑（AI / 套卷 / 判分 / 缓存）
│   │   ├── core/          配置、数据库、鉴权
│   │   └── main.py        应用入口
│   ├── tests/             pytest
│   ├── alembic/           数据库迁移
│   └── import_data/       题库 JSON
├── web/
│   └── src/
│       ├── views/         24 个页面
│       ├── api/           axios 封装与拦截器
│       ├── router/
│       ├── stores/        Pinia
│       └── styles/        global.css（设计 token 都在这）
├── deployer/              三套部署工具
├── docs/                  截图 + 文档
└── .github/workflows/     CI
```

---

## 本地开发

### 后端

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

接口文档：`http://localhost:8001/api/docs`

首次启动会自动建表 + 创建 `admin / admin123`。

### 前端

```bash
cd web
npm install
npm run dev     # http://localhost:5173，已配代理到 8001
npm run build   # 产物在 dist/app
```

> `vite.config.js` 里 `base` 是 `/chem/app/`，改学科时要同步改。

---

## 关键约定

### 枚举值用小写

数据库里存 `single` / `medium`，不是 `SINGLE` / `MEDIUM`：

```python
question_type = Column(
    Enum(QuestionType, values_callable=lambda x: [e.value for e in x]),
    default=QuestionType.SINGLE,
)
```

漏了 `values_callable` 会存成大写，与导入的题库数据和前端筛选参数对不上。

### 数据库文件按学科命名

`chemlearn.db` / `mathlearn.db` / `physicslearn.db` / ...

导入脚本用 `CHEMLEARN_DB` 环境变量指定路径（各学科沿用同一个变量名）。

### 前端路径前缀

`/{学科}/app/`（页面）、`/{学科}/api/v1`（接口）。nginx 去掉前缀转发到 `127.0.0.1:{端口}/`。

---

## 开发时踩过的坑

这些是实际遇到并修掉的，改相关代码时注意：

### 1. SQLAlchemy JSON 列不追踪内部改动

```python
paper.questions_json = questions   # 元素被原地改过，可能判定未变化
```

需要显式标记：

```python
from sqlalchemy.orm.attributes import flag_modified
flag_modified(paper, "questions_json")
```

**症状**：算出来 100，数据库还是 98。

### 2. 后台任务不能依赖同步调用做兜底

```python
try:
    ...
except Exception as e:
    task.status = "failed"
    task.finished_at = datetime.now(...)   # datetime 没 import → except 自己抛错
```

**症状**：任务永远卡在 `running`，前端一直转圈。

### 3. 浏览器会把后台标签的定时器节流

倒计时不能用 `remain--`，要用绝对时间：

```js
const left = Math.round((deadline - Date.now()) / 1000)
```

**症状**：学生切到别的标签查答案，倒计时几乎不走。

### 4. 401 要分场景

响应拦截器里不能把所有 401 都当「登录过期」：

```js
const isAuth = /\/auth\/(login|register)/.test(config.url)
if (status === 401) {
  if (isAuth) ElMessage.error(detail || '用户名或密码错误')
  else { /* 清 token + 跳登录 */ }
}
```

**症状**：密码输错提示「登录已过期」。

### 5. AI 输出的 JSON 可能含非法转义

试卷文本里的 `\%`、`\(` 会被原样输出：

```python
re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", s)   # 只转义非法序列
```

### 6. 别全信 AI 的题型判断

英语卷结构特征明显，用规则兜底更稳：

```python
if passage:
    qtype = "cloze" if re.search(r"_{2,}", passage) else "reading"
```

---

## 测试

```bash
cd backend
pytest -v                    # 全部
pytest tests/test_auth.py    # 单个文件
```

CI（`.github/workflows/ci.yml`）每次 push 会跑：

1. `pytest`
2. 启动服务，请求 `/api/health` 和登录接口，确认 200

---

## 加一个新学科

1. 复制 `化学/` 目录改个名
2. 改 `.env` 的端口和数据库文件名
3. 改 `web/vite.config.js` 的 `base`、`src/api/index.js` 的 `baseURL`
4. `npm run build`
5. 加 systemd 服务 + nginx location
6. 题库导入时设 `CHEMLEARN_DB` 指向新库

或者直接用部署器（它按 `SUBJECTS` 列表循环处理）。

---

## 提交规范

```
feat: 新功能
fix: 修 bug
docs: 文档
refactor: 重构
```

提交信息里写清楚**为什么改**，不只是改了什么。比如：

```
fix: 倒计时改用绝对时间重算

原来用递减计数器，浏览器会把后台标签的定时器节流到每分钟 1 次，
学生切到别的标签就等于停表。
```
