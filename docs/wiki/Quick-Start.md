# 快速开始

两种方式，按你的场景选：

| 场景 | 方式 | 耗时 |
|---|---|---|
| 有一台全新 Linux 服务器 | [方式一：一键部署](#方式一一键部署推荐) | 3–6 分钟 |
| 只想在自己电脑上看看 | [方式二：Windows 免安装版](#方式二windows-免安装) | 1 分钟 |
| 想改代码 | [方式三：本地开发](#方式三本地开发) | 5 分钟 |

---

## 方式一：一键部署（推荐）

### 前提

- 一台**全新的** Ubuntu 20.04+ 或 Debian 11+ 服务器，能联网
- 建议 2 核 4G，磁盘 20G 以上
- 云服务器需要提前在安全组放行你要用的端口（默认 80）

### 步骤

1. 下载 `ChemLearn-Deployer-v1.3.0.exe`（[Releases 页面](https://github.com/houshibo0101/chemlearn/releases)）
2. 双击运行，浏览器会自动打开部署界面
3. 填写：

   | 字段 | 说明 |
   |---|---|
   | 服务器 IP | 例如 `192.168.1.100` |
   | SSH 端口 | 默认 22 |
   | 用户名 | 有 sudo 权限的账号，通常是 `root` |
   | 密码 | SSH / sudo 密码 |
   | Web 访问端口 | 默认 80，被占用可填 8080 |
   | **AI API Key** | 火山引擎方舟的 Key，例如 `ark-...` |
   | 模型名称 | 默认 `doubao-seed-2-0-mini-260428` |
   | 解析模型 | 选填，留空则与上面相同 |

4. 点「开始部署」，等 3–6 分钟，看到绿色日志即完成
5. 打开 `http://服务器IP/`，用 `admin / admin123` 登录

> **AI 配置在部署时就写进各学科 `backend/.env` 了**，装完即用，不用再登录服务器改配置。
> 如果暂时没有 Key，勾选「暂不配置 AI」也能部署，只是 AI 功能不可用。

### 部署器做了什么

```
1. 装 nginx / python3-venv / curl
2. 检查并放行 ufw 端口
3. 解压内置部署包到 /home/<用户>/studycenter
4. 写入 backend/.env（AI 配置）
5. 建 venv 并装 Python 依赖（清华镜像，失败自动换官方源）
6. 注册 systemd 服务、配置 nginx、启动
7. 健康检查：逐个端口探测 /api/health，检查 SPA 深链接
```

---

## 方式二：Windows 免安装

下载 `化学学习系统Windows版.exe`（27 MB），双击即用：

- 会自动解压到 `%LOCALAPPDATA%\ChemLearnWindows`
- 自动挑一个空闲端口启动，浏览器自动打开
- 数据就存在那个目录里，拷走目录就是备份

> 只监听本机，同学访问需要走局域网 IP（启动日志里会打印）。

---

## 方式三：本地开发

```bash
# 1. 克隆
git clone https://github.com/houshibo0101/chemlearn.git
cd chemlearn

# 2. 后端
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt

# 3. 配置（可选，不配则 AI 功能不可用）
cp .env.example .env
# 编辑 .env，填 AI_API_KEY 等

# 4. 启动
uvicorn app.main:app --reload --port 8001

# 5. 前端（另开终端）
cd ../web
npm install
npm run dev
```

前端开发服务器默认 `http://localhost:5173`，已配好代理到 8001。

首次启动会自动建表并创建管理员 `admin / admin123`。

### 导入题库

题库不再内置在源码里，从 [Releases](https://github.com/houshibo0101/chemlearn/releases/tag/question-bank-v1) 下载：

```bash
# 解压到 backend/import_data/ 后
cd backend
python import_gaokao_unified.py          # 导入全部
python import_gaokao_unified.py --list   # 只看有哪些批次
python import_gaokao_unified.py gaokao   # 只导某一批
```

---

## 下一步

- 功能怎么用 → [功能说明](Features)
- AI 怎么配 → [AI 配置](AI-Setup)
- 出问题了 → [常见问题](FAQ)
