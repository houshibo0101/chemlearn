#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""化学学习系统 · Windows 本地部署器

把整套系统（前端 + 后端 + 题库）打包进一个 exe，双击后：
    1. 把运行时文件部署到 %LOCALAPPDATA%\\ChemLearnWindows
    2. 在本机启动服务（默认 8000，被占用自动避让）
    3. 自动打开浏览器，局域网内其它设备也能访问

运行期不需要安装 Python、数据库或任何服务器软件，所有依赖已经打进 exe。

用法：
    ChemLearnWindows.exe                    图形界面，双击即用
    ChemLearnWindows.exe --port 8090        指定端口
    ChemLearnWindows.exe --no-browser       启动后不自动打开浏览器
    ChemLearnWindows.exe --reset            重新部署（清空用户数据，恢复内置题库）
    ChemLearnWindows.exe --console          纯命令行模式（排障用，窗口里能看到日志）
"""
VERSION = "2.1.0"
APP_NAME = "化学学习系统"
DATA_FOLDER = "ChemLearnWindows"
PAYLOAD_NAME = "payload_chem.tar.gz"
URL_PREFIX = "/chem"
APP_PATH = URL_PREFIX + "/app/"

import argparse
import copy
import hashlib
import json
import os
import queue
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import urllib.request
import webbrowser

if os.name == "nt":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


# --------------------------------------------------------------------------- 基础工具

def resource_path(name):
    """exe 内嵌资源路径（PyInstaller 解包目录）"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def default_data_root():
    override = os.environ.get("CHEMLEARN_HOME", "").strip()
    if override:
        return os.path.abspath(override)
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, DATA_FOLDER)


DATA_ROOT = default_data_root()
BACKEND_DIR = os.path.join(DATA_ROOT, "backend")
WEB_DIR = os.path.join(DATA_ROOT, "web", "dist", "app")
DB_PATH = os.path.join(BACKEND_DIR, "chemlearn.db")
ENV_PATH = os.path.join(BACKEND_DIR, ".env")
MARKER = os.path.join(DATA_ROOT, ".deployed")
LOG_PATH = os.path.join(DATA_ROOT, "deployer.log")
PAYLOAD_PATH = resource_path(PAYLOAD_NAME)
# v1（单文件运行器）把数据放在 <数据目录>\化学\backend，升级时接管它
LEGACY_DB = os.path.join(DATA_ROOT, "化学", "backend", "chemlearn.db")
LEGACY_MARKER = os.path.join(DATA_ROOT, ".extracted")


def human_size(num):
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return "%.0f %s" % (num, unit) if unit == "B" else "%.1f %s" % (num, unit)
        num /= 1024.0


def append_log_file(text):
    try:
        os.makedirs(DATA_ROOT, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except Exception:
        pass


# --------------------------------------------------------------------------- 部署

class DeployError(RuntimeError):
    pass


def payload_fingerprint():
    """版本 + payload 内容哈希。

    不能用 mtime：PyInstaller 单文件每次启动都解包到新的临时目录，mtime 每次
    都变，会误判成“有新版本”而反复解压。
    """
    try:
        digest = hashlib.sha256()
        with open(PAYLOAD_PATH, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                digest.update(chunk)
        return "%s-%d-%s" % (VERSION, os.path.getsize(PAYLOAD_PATH),
                             digest.hexdigest()[:16])
    except OSError:
        return VERSION


def read_marker():
    try:
        with open(MARKER, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_env_if_missing():
    """首次部署写入 .env：DEBUG 打开（本地使用）并生成随机 SECRET_KEY"""
    if os.path.exists(ENV_PATH):
        return
    secret = secrets.token_urlsafe(48)
    with open(ENV_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(
            "# 由本地部署器自动生成\n"
            "# 本机使用保持 DEBUG=true；若对外开放请改为 false 并设置强密码\n"
            "DEBUG=true\n"
            "SECRET_KEY=%s\n" % secret
        )


def force_clean(log, timeout=8.0):
    """清空数据目录（保留日志）。

    刚停掉服务时 SQLite 句柄可能还没释放，Windows 上会短暂锁住 chemlearn.db，
    所以这里带重试；仍然失败就明确报错，而不是让后面的解压失败得莫名其妙。
    """
    deadline = time.time() + timeout
    while True:
        failed = []
        for name in os.listdir(DATA_ROOT):
            if name in (".deployed", "deployer.log"):
                continue
            target = os.path.join(DATA_ROOT, name)
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                else:
                    os.remove(target)
            except OSError as exc:
                failed.append("%s（%s）" % (name, exc))
        if not failed:
            return
        if time.time() > deadline:
            raise DeployError(
                "无法清空数据目录，文件正被占用：\n  "
                + "\n  ".join(failed[:5])
                + "\n请完全关闭所有部署器窗口后重试。")
        time.sleep(0.4)


def deploy(force=False, log=print, progress=None):
    """解压运行时到数据目录；升级时保留数据库与上传文件。"""
    if not os.path.exists(PAYLOAD_PATH):
        raise DeployError("exe 内缺少运行时包 %s（请重新下载完整的部署器）" % PAYLOAD_NAME)

    fp = payload_fingerprint()
    first_run = not os.path.isdir(BACKEND_DIR)
    marker = read_marker()
    up_to_date = (not force and not first_run
                  and marker.get("fingerprint") == fp
                  and os.path.isfile(os.path.join(WEB_DIR, "index.html")))
    if up_to_date:
        log("运行环境已是最新（%s）" % VERSION)
        if progress:
            progress(100)
        return False

    os.makedirs(DATA_ROOT, exist_ok=True)

    # 从 v1 升级：先把旧目录里的数据库接管过来，别让用户题库“消失”
    migrated = False
    if not force and first_run and not os.path.exists(DB_PATH) and os.path.isfile(LEGACY_DB):
        os.makedirs(BACKEND_DIR, exist_ok=True)
        shutil.copy2(LEGACY_DB, DB_PATH)
        migrated = True
        log("检测到旧版部署数据，已接管原有题库与账号（升级后数据不变）")

    if force:
        log("清空本机数据并重新部署（用户数据将丢失）…")
        force_clean(log)
    elif first_run:
        log("首次运行，正在部署运行环境到：%s" % DATA_ROOT)
    else:
        log("检测到新版本，正在更新运行时文件（数据库与上传文件保留）…")
        # 前端文件名带哈希、后端代码整体替换，避免旧文件残留
        shutil.rmtree(os.path.join(DATA_ROOT, "web"), ignore_errors=True)
        shutil.rmtree(os.path.join(BACKEND_DIR, "app"), ignore_errors=True)

    total = os.path.getsize(PAYLOAD_PATH)
    done = 0
    keep_db = (not force) and os.path.exists(DB_PATH)
    db_member = None
    with tarfile.open(PAYLOAD_PATH, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            # 数据库最后单独落盘：升级时不能覆盖用户题库；首次部署也不能
            # 因为解压中途被关掉而留下半个 chemlearn.db
            if member.name.endswith("backend/chemlearn.db"):
                db_member = member
                continue
            try:
                tar.extract(member, DATA_ROOT, filter="data")  # py3.12+ 防路径穿越
            except TypeError:
                tar.extract(member, DATA_ROOT)
            done += max(member.size, 0)
            if progress and total:
                progress(min(99, int(done * 100 / max(total, 1))))

        if db_member is not None and not keep_db:
            temp_info = copy.copy(db_member)
            temp_info.name = db_member.name + ".tmp"
            try:
                tar.extract(temp_info, DATA_ROOT, filter="data")
            except TypeError:
                tar.extract(temp_info, DATA_ROOT)
            os.replace(os.path.join(BACKEND_DIR, "chemlearn.db.tmp"), DB_PATH)

    if not os.path.isdir(BACKEND_DIR):
        raise DeployError("解压后没有找到 backend 目录，运行时包可能已损坏")
    os.makedirs(os.path.join(BACKEND_DIR, "uploads"), exist_ok=True)
    write_env_if_missing()

    # 旧版目录已无用（数据库在迁移时已接管），清掉避免重复占空间
    if migrated or os.path.isfile(LEGACY_MARKER):
        shutil.rmtree(os.path.join(DATA_ROOT, "化学"), ignore_errors=True)
        shutil.rmtree(os.path.join(DATA_ROOT, "portal"), ignore_errors=True)
        try:
            os.remove(LEGACY_MARKER)
        except OSError:
            pass
        log("已清理旧版运行时目录")

    with open(MARKER, "w", encoding="utf-8") as f:
        json.dump({
            "version": VERSION,
            "fingerprint": fp,
            "deployed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, f, ensure_ascii=False, indent=2)

    if progress:
        progress(100)
    log("运行环境就绪：%s" % DATA_ROOT)
    return True


def payload_meta():
    try:
        with open(os.path.join(DATA_ROOT, "payload.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# --------------------------------------------------------------------------- 网络

def port_free(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def find_port(preferred, span=40):
    for port in range(preferred, min(preferred + span, 65536)):
        if port_free(port):
            return port
    return None


def lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
    finally:
        sock.close()


def lan_url(port):
    ip = lan_ip()
    if not ip or ip.startswith("127."):
        return ""
    return "http://%s:%d%s" % (ip, port, APP_PATH)


def health_ok(port, timeout=1.5):
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/api/health" % port, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


# --------------------------------------------------------------------------- 服务

def build_app(app):
    """本机没有 nginx 做路径转发，这里补两件事：
    1) /chem/xxx -> /xxx（前端产物按 /chem/ 前缀构建）
    2) / -> 302 到 /chem/app/（只输 IP:端口 也能进）
    """
    from starlette.requests import Request
    from starlette.responses import RedirectResponse

    async def wrapped(scope, receive, send):
        if scope.get("type") not in ("http", "websocket"):
            await app(scope, receive, send)
            return
        path = scope.get("path", "") or "/"
        if path == "/":
            request = Request(scope)
            response = RedirectResponse(APP_PATH, status_code=302)
            await response(request.scope, receive, send)
            return
        if path == URL_PREFIX or path.startswith(URL_PREFIX + "/"):
            scope = dict(scope)
            new_path = path[len(URL_PREFIX):] or "/"
            scope["path"] = new_path
            scope["raw_path"] = new_path.encode("utf-8")
        await app(scope, receive, send)

    return wrapped


class Backend:
    """uvicorn 服务，跑在后台线程里，可停止。"""

    def __init__(self, port, log):
        self.port = port
        self.log = log
        self.server = None
        self.thread = None
        self.error = None

    def _quiet_sqlalchemy(self):
        import logging
        for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine",
                     "sqlalchemy.pool", "sqlalchemy.dialects", "sqlalchemy.orm"):
            logging.getLogger(name).setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    def start(self):
        import uvicorn

        os.chdir(BACKEND_DIR)
        if BACKEND_DIR not in sys.path:
            sys.path.insert(0, BACKEND_DIR)
        # 后端按相对路径找数据库 / 前端 / 上传目录，工作目录必须是 backend
        self._quiet_sqlalchemy()

        from app.main import app as fastapi_app  # noqa: E402

        try:
            from app.core import database as _db
            for name in ("engine", "async_engine"):
                engine = getattr(_db, name, None)
                if engine is not None:
                    engine.echo = False
        except Exception:
            pass

        config = uvicorn.Config(
            build_app(fastapi_app),
            host="0.0.0.0",
            port=self.port,
            log_level="info",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self._run, name="uvicorn", daemon=True)
        self.thread.start()

    def _run(self):
        try:
            self.server.run()
        except BaseException:
            self.error = traceback.format_exc()
            self.log("服务线程异常退出：\n" + self.error)

    def wait_ready(self, timeout=90):
        """以健康检查为最终标准：抗杀毒软件首次扫描导致的慢启动"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.error:
                return False
            if health_ok(self.port):
                return True
            if self.thread and not self.thread.is_alive():
                # 线程已退出且没抓到异常，说明服务没能起来
                return False
            time.sleep(0.3)
        return False

    def stop(self, timeout=6):
        if self.server is not None:
            self.server.should_exit = True
        if self.thread is not None:
            self.thread.join(timeout)
            return not self.thread.is_alive()
        return True


# --------------------------------------------------------------------------- 日志输出重定向（GUI 里显示 uvicorn / 后端日志）

class QueueWriter:
    def __init__(self, emit):
        self.emit = emit
        self._buf = ""

    def write(self, text):
        if not text:
            return 0
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self.emit(line.rstrip())
        return len(text)

    def flush(self):
        if self._buf.strip():
            self.emit(self._buf.rstrip())
        self._buf = ""

    def isatty(self):
        return False


# --------------------------------------------------------------------------- 图形界面

BG = "#f3f4f6"
CARD = "#ffffff"
BORDER = "#e5e7eb"
TEXT = "#111827"
MUTED = "#6b7280"
ACCENT = "#4f46e5"
ACCENT_DARK = "#4338ca"
OK = "#059669"
WARN = "#d97706"
ERR = "#dc2626"


class DeployerApp:
    def __init__(self, root, port=8000, auto_browser=True, reset=False):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.port = port
        self.auto_browser = auto_browser
        self.reset_requested = reset
        self.backend = None
        self.ready = False
        self.starting = False
        self.stopping = False
        self.stop_done = threading.Event()
        self.messages = queue.Queue()

        # 高 DPI 屏（如 200% 缩放）下按比例放大窗口与间距，避免文字发虚或挤在一起
        try:
            self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        except Exception:
            self.scale = 1.0

        def px(value):
            return int(round(value * self.scale))

        self.px = px

        self._build_ui()
        self._redirect_streams()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(120, self._drain)
        self.root.after(200, self.start)

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        tk, ttk, px = self.tk, self.ttk, self.px
        root = self.root
        root.title("%s · Windows 本地部署器  v%s" % (APP_NAME, VERSION))
        root.configure(bg=BG)
        root.geometry("%dx%d" % (px(760), px(580)))
        root.minsize(px(720), px(560))

        try:
            root.iconbitmap(resource_path("app.ico"))
        except Exception:
            pass

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Deployer.Horizontal.TProgressbar",
                        background=ACCENT, troughcolor="#e9edf5",
                        lightcolor=ACCENT, darkcolor=ACCENT,
                        bordercolor="#e9edf5", thickness=px(9))

        header = tk.Frame(root, bg=ACCENT, height=px(86))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="%s · 本地部署器" % APP_NAME, bg=ACCENT, fg="white",
                 font=("Microsoft YaHei UI", 15, "bold")).pack(
            anchor="w", padx=px(22), pady=(px(14), 0))
        tk.Label(header, text="双击即用 · 无需安装 Python / 数据库 · 局域网可访问",
                 bg=ACCENT, fg="#e0e7ff",
                 font=("Microsoft YaHei UI", 9)).pack(anchor="w", padx=px(22),
                                                      pady=(px(4), 0))
        tk.Label(header, text="v" + VERSION, bg=ACCENT, fg="#c7d2fe",
                 font=("Consolas", 9)).place(relx=1.0, x=-px(22), y=px(18),
                                             anchor="ne")

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=px(18), pady=(px(14), 0))

        # 状态条
        status_card = tk.Frame(body, bg=CARD, highlightthickness=1,
                               highlightbackground=BORDER)
        status_card.pack(fill="x")
        self.status_dot = tk.Label(status_card, text="●", bg=CARD, fg=WARN,
                                   font=("Segoe UI", 12))
        self.status_dot.pack(side="left", padx=(px(14), px(6)), pady=px(10))
        self.status_label = tk.Label(status_card, text="正在准备…", bg=CARD, fg=TEXT,
                                     font=("Microsoft YaHei UI", 10, "bold"))
        self.status_label.pack(side="left", pady=px(10))
        self.progress = ttk.Progressbar(status_card, mode="determinate",
                                        length=px(150), maximum=100,
                                        style="Deployer.Horizontal.TProgressbar")
        self.progress.pack(side="right", padx=px(14))

        # 日志
        log_card = tk.Frame(body, bg=CARD, highlightthickness=1,
                            highlightbackground=BORDER)
        log_card.pack(fill="both", expand=True, pady=px(10))
        self.log_text = tk.Text(log_card, bg="#0f172a", fg="#cbd5e1", bd=0,
                                font=("Consolas", 9), wrap="word", height=10,
                                insertbackground="white", padx=px(10), pady=px(8))
        scroll = ttk.Scrollbar(log_card, orient="vertical",
                               command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set, state="disabled")
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # 访问地址
        access_card = tk.Frame(body, bg=CARD, highlightthickness=1,
                               highlightbackground=BORDER)
        access_card.pack(fill="x")

        self.local_var = tk.StringVar(value="—")
        self.lan_var = tk.StringVar(value="—")
        self._url_row(access_card, "本机访问", self.local_var,
                      lambda: self.open_url(self.local_var.get()), "打开", 0)
        self._url_row(access_card, "局域网访问", self.lan_var,
                      lambda: self.copy(self.lan_var.get()), "复制", 1)

        # 底部操作
        footer = tk.Frame(body, bg=BG)
        footer.pack(fill="x", pady=(px(8), px(12)))

        port_box = tk.Frame(footer, bg=BG)
        port_box.pack(side="left")
        tk.Label(port_box, text="端口", bg=BG, fg=MUTED,
                 font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.port_var = tk.StringVar(value=str(self.port))
        self.port_spin = ttk.Spinbox(port_box, from_=1024, to=65535, width=7,
                                     textvariable=self.port_var,
                                     font=("Consolas", 9))
        self.port_spin.pack(side="left", padx=(px(6), px(12)))
        self.browser_var = tk.BooleanVar(value=self.auto_browser)
        check = tk.Frame(port_box, bg=BG)
        check.pack(side="left")
        size = px(15)
        self.browser_canvas = tk.Canvas(check, width=size, height=size, bg=BG,
                                        highlightthickness=0, bd=0, cursor="hand2")
        self.browser_canvas.pack(side="left")
        self.browser_label = tk.Label(check, text="启动后自动打开浏览器", bg=BG,
                                      fg=TEXT, font=("Microsoft YaHei UI", 9),
                                      cursor="hand2")
        self.browser_label.pack(side="left", padx=(px(6), 0))
        for widget in (self.browser_canvas, self.browser_label):
            widget.bind("<Button-1>", self.toggle_browser)
        self._draw_browser_box()

        self.btn_quit = self._button(footer, "退出", self.on_close, primary=False)
        self.btn_stop = self._button(footer, "停止服务", self.stop_service, primary=False)
        self.btn_redeploy = self._button(footer, "重新部署…", self.redeploy, primary=False)
        self.btn_data = self._button(footer, "数据目录", self.open_data_dir, primary=False)
        self.btn_open = self._button(footer, "打开系统", self.open_system, primary=True)
        self.btn_retry = self._button(footer, "重试启动", self.retry_start, primary=True)
        for btn in (self.btn_quit, self.btn_stop, self.btn_redeploy,
                    self.btn_data, self.btn_open):
            btn.pack(side="right", padx=(px(8), 0))
        self.btn_open.configure(state="disabled")
        self.btn_stop.configure(state="disabled")

    def _url_row(self, parent, label, var, command, btn_text, row):
        tk, px = self.tk, self.px
        top = px(9) if row == 0 else px(4)
        bottom = px(4)
        tk.Label(parent, text=label, bg=CARD, fg=MUTED,
                 font=("Microsoft YaHei UI", 9)).grid(
            row=row, column=0, sticky="w", padx=(px(14), px(8)),
            pady=(top, bottom))
        entry = tk.Entry(parent, textvariable=var, state="readonly", bd=0,
                         readonlybackground=CARD, fg=TEXT,
                         font=("Consolas", 10), justify="left")
        entry.grid(row=row, column=1, sticky="we", pady=(top, bottom))
        tk.Button(parent, text=btn_text, command=command, bd=0, relief="flat",
                  bg="#eef2ff", fg=ACCENT_DARK, activebackground="#e0e7ff",
                  font=("Microsoft YaHei UI", 9), cursor="hand2", padx=px(12),
                  pady=px(1)).grid(row=row, column=2, padx=(px(8), px(14)),
                                   pady=(top, bottom))
        parent.grid_columnconfigure(1, weight=1)

    def _button(self, parent, text, command, primary=False):
        tk, px = self.tk, self.px
        if primary:
            return tk.Button(parent, text=text, command=command, bd=0,
                             relief="flat", bg=ACCENT, fg="white",
                             activebackground=ACCENT_DARK, activeforeground="white",
                             font=("Microsoft YaHei UI", 9, "bold"),
                             cursor="hand2", padx=px(18), pady=px(5))
        return tk.Button(parent, text=text, command=command, bd=0, relief="flat",
                         bg="#e5e7eb", fg=TEXT, activebackground="#d1d5db",
                         font=("Microsoft YaHei UI", 9), cursor="hand2",
                         padx=px(14), pady=px(5))

    def _draw_browser_box(self):
        """自绘勾选框：ttk 的指示器在 clam 主题下太淡，看着像坏掉了"""
        canvas = self.browser_canvas
        canvas.delete("all")
        size = self.px(15)
        canvas.configure(width=size, height=size)
        if self.browser_var.get():
            canvas.create_rectangle(1, 1, size - 1, size - 1,
                                    fill=ACCENT, outline=ACCENT)
            canvas.create_line(size * 0.24, size * 0.52,
                               size * 0.43, size * 0.72,
                               size * 0.78, size * 0.28,
                               fill="white", width=max(2, self.px(2)),
                               capstyle="round", joinstyle="round")
        else:
            canvas.create_rectangle(1, 1, size - 1, size - 1,
                                    fill=CARD, outline="#9ca3af")

    def toggle_browser(self, _event=None):
        self.browser_var.set(not self.browser_var.get())
        self._draw_browser_box()

    # ---------------------------------------------------------------- 日志
    def _redirect_streams(self):
        writer = QueueWriter(lambda line: self.messages.put(("log", line)))
        sys.stdout = writer
        sys.stderr = writer

    def log(self, text):
        self.messages.put(("log", str(text)))

    def status(self, text, color=MUTED):
        self.messages.put(("status", text, color))

    def set_progress(self, value):
        self.messages.put(("progress", value))

    def _drain(self):
        dirty = False
        try:
            while True:
                item = self.messages.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._append_log(item[1])
                    append_log_file(item[1])
                    dirty = True
                elif kind == "status":
                    self.status_label.configure(text=item[1])
                    self.status_dot.configure(fg=item[2])
                    dirty = True
                elif kind == "progress":
                    self.progress.configure(mode="determinate")
                    self.progress["value"] = item[1]
                    dirty = True
                elif kind == "ready":
                    self._on_ready(item[1])
                    dirty = True
                elif kind == "failed":
                    self._on_failed(item[1])
                    dirty = True
        except queue.Empty:
            pass
        if dirty:
            self.root.update_idletasks()
        self.root.after(80, self._drain)

    def _append_log(self, line):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        # 日志区最多保留 2000 行，避免长时间运行吃内存
        if int(self.log_text.index("end-1c").split(".")[0]) > 2000:
            self.log_text.delete("1.0", "200.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ---------------------------------------------------------------- 启动流程
    def start(self):
        if self.starting or self.ready:
            return
        self.starting = True
        self.port = self._safe_port()
        self.port_var.set(str(self.port))
        self.port_spin.configure(state="disabled")
        self.btn_retry.pack_forget()
        self.status("正在部署运行环境…", WARN)
        self.progress.configure(mode="indeterminate")
        self.progress.start(12)
        thread = threading.Thread(target=self._start_worker,
                                  args=(self.reset_requested,), daemon=True)
        thread.start()

    def _start_worker(self, reset):
        try:
            deploy(force=reset, log=self.log, progress=self.set_progress)
            self.reset_requested = False   # 重置只需在第一次部署时生效
            meta = payload_meta()
            if meta.get("questions"):
                self.log("内置题库：%s 题" % meta["questions"])

            port = find_port(self.port)
            if port is None:
                raise DeployError("从 %d 起连续 40 个端口都被占用，请换一个端口再试" % self.port)
            if port != self.port:
                self.log("端口 %d 已被占用，自动改用 %d" % (self.port, port))
            self.port = port

            self.status("等待服务就绪…", WARN)
            self.log("启动服务 0.0.0.0:%d（局域网可访问）" % port)
            self.backend = Backend(port, self.log)
            self.backend.start()
            if not self.backend.wait_ready():
                detail = "服务启动失败"
                if self.backend.error:
                    detail += "：" + self.backend.error.strip().splitlines()[-1]
                raise DeployError("%s（端口 %d），请查看上方日志" % (detail, port))

            self.messages.put(("ready", {"port": port}))
        except DeployError as exc:
            self.messages.put(("failed", str(exc)))
        except Exception:
            self.messages.put(("failed", traceback.format_exc()))

    def _on_ready(self, info):
        self.starting = False
        self.ready = True
        port = info["port"]
        local = "http://127.0.0.1:%d%s" % (port, APP_PATH)
        lan = lan_url(port)
        self.local_var.set(local)
        self.lan_var.set(lan or "（未检测到局域网 IP，请检查网络连接）")
        self.port_var.set(str(port))
        self.port_spin.configure(state="disabled")
        self.btn_retry.pack_forget()
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress["value"] = 100
        self.status("已启动 · 运行中", OK)
        self.btn_open.configure(state="normal")
        self.btn_stop.configure(state="normal")

        self.log("")
        self.log("=" * 58)
        self.log("  %s 已在本机部署并启动" % APP_NAME)
        self.log("  本机访问：  " + local)
        if lan:
            self.log("  局域网访问：" + lan)
        self.log("  管理账号：  admin / admin123（登录后请及时修改密码）")
        self.log("  数据目录：  " + DATA_ROOT)
        self.log("  停止服务：  点“停止服务”或直接关闭本窗口")
        self.log("=" * 58)

        if self.browser_var.get():
            self.root.after(300, lambda: webbrowser.open(local))

    def _on_failed(self, message):
        from tkinter import messagebox

        self.starting = False
        self.ready = False
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress["value"] = 0
        self.status("启动失败", ERR)
        self.log("")
        self.log("启动失败：" + message)
        self.btn_stop.configure(state="normal" if self.backend else "disabled")
        self.btn_open.configure(state="disabled")
        self.port_spin.configure(state="normal")
        self.btn_retry.pack(side="right", padx=(self.px(8), 0),
                            after=self.btn_open)
        messagebox.showerror(
            "启动失败",
            "部署没有完成，请查看窗口中的日志。\n\n"
            + message.strip().splitlines()[-1][:400])

    def retry_start(self):
        if self.starting or self.ready:
            return
        self.btn_retry.pack_forget()
        self.port_spin.configure(state="disabled")
        try:
            self.port = int(self.port_var.get())
        except Exception:
            self.port = 8000
            self.port_var.set("8000")
        self.start()

    # ---------------------------------------------------------------- 操作
    def open_url(self, url):
        if url and url.startswith("http"):
            webbrowser.open(url)

    def open_system(self):
        self.open_url(self.local_var.get())

    def open_data_dir(self):
        try:
            os.startfile(DATA_ROOT)
        except Exception as exc:
            self.log("打开数据目录失败：%s" % exc)

    def copy(self, text):
        if not text or not text.startswith("http"):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status("局域网地址已复制", OK)

    def stop_service(self):
        if not self.backend or self.stopping:
            return
        self.stopping = True
        self.stop_done.clear()
        self.status("正在停止服务…", WARN)
        self.btn_stop.configure(state="disabled")
        self.btn_open.configure(state="disabled")
        backend = self.backend

        def worker():
            backend.stop()
            self.backend = None
            self.ready = False
            self.stop_done.set()

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(150, self._finish_stop)

    def _finish_stop(self):
        if not self.stop_done.is_set():
            self.root.after(150, self._finish_stop)
            return
        self.stopping = False
        self.status("已停止", MUTED)
        self.log("服务已停止。可点“重试启动”重新运行，或点“退出”关闭窗口。")
        self.progress["value"] = 0
        self.btn_open.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        self.port_spin.configure(state="normal")
        self.btn_retry.pack(side="right", padx=(self.px(8), 0),
                            after=self.btn_open)

    def _spawn_new_instance(self, extra):
        if getattr(sys, "frozen", False):
            cmd = [sys.executable] + extra
            cwd = os.path.dirname(os.path.abspath(sys.executable))
        else:
            cmd = [sys.executable, os.path.abspath(__file__)] + extra
            cwd = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen(cmd, cwd=cwd or None, close_fds=True)

    def redeploy(self):
        from tkinter import messagebox

        if not messagebox.askyesno(
                "重新部署",
                "将清空本机上的全部数据（用户、班级、练习记录），\n"
                "把题库恢复为内置版本。\n\n确定继续吗？"):
            return
        self.status("正在重新部署…", WARN)
        self.log("重新部署：停止当前服务，并启动新的部署器实例执行重置")
        if self.backend:
            self.backend.stop(timeout=4)
            self.backend = None
        self.ready = False
        self.btn_open.configure(state="disabled")
        self.btn_stop.configure(state="disabled")
        try:
            extra = ["--reset", "--port", str(self._safe_port())]
            if not self.browser_var.get():
                extra.append("--no-browser")
            self._spawn_new_instance(extra)
        except Exception:
            self.log("启动新实例失败，请手动关闭后重新双击运行：\n"
                     + traceback.format_exc())
            self.status("重新部署失败", ERR)
            return
        self.root.after(400, self.root.destroy)

    def _safe_port(self):
        try:
            port = int(self.port_var.get())
            return port if 1 <= port <= 65535 else 8000
        except Exception:
            return self.port

    def on_close(self):
        if self.backend:
            self.status("正在停止服务…", WARN)
            self.backend.stop(timeout=4)
            self.backend = None
        try:
            self.root.destroy()
        except Exception:
            pass


def enable_dpi_awareness():
    """让窗口按真实 DPI 渲染（否则 200% 缩放下整窗被位图放大，文字发虚）"""
    if os.name != "nt":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)   # 系统 DPI 感知
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def run_gui(args):
    import tkinter as tk

    enable_dpi_awareness()
    root = tk.Tk()
    DeployerApp(root, port=args.port,
                auto_browser=not args.no_browser,
                reset=args.reset or args.reinstall)
    root.mainloop()
    return 0


# --------------------------------------------------------------------------- 命令行模式

def run_console(args):
    print("")
    print("  %s · Windows 本地部署器  v%s" % (APP_NAME, VERSION))
    print("  " + "-" * 56)

    deploy(force=args.reset or args.reinstall)
    port = find_port(args.port)
    if port is None:
        print("错误：从 %d 起连续 40 个端口都被占用" % args.port)
        return 2
    if port != args.port:
        print("端口 %d 已被占用，自动改用 %d" % (args.port, port))

    backend = Backend(port, print)
    backend.start()
    if not backend.wait_ready():
        print("错误：服务启动失败（端口 %d）" % port)
        backend.stop()
        return 3

    local = "http://127.0.0.1:%d%s" % (port, APP_PATH)
    lan = lan_url(port)
    print("")
    print("=" * 60)
    print("  %s 已启动" % APP_NAME)
    print("  本机访问：  " + local)
    if lan:
        print("  局域网访问：" + lan)
    print("  管理账号：  admin / admin123（登录后请修改密码）")
    print("  数据目录：  " + DATA_ROOT)
    print("  停止服务：  Ctrl+C")
    print("=" * 60)
    print("")
    if not args.no_browser:
        webbrowser.open(local)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n正在停止…")
    finally:
        backend.stop()
    return 0


# --------------------------------------------------------------------------- 入口

def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="ChemLearnWindows",
        description="%s Windows 本地部署器" % APP_NAME)
    parser.add_argument("--port", type=int, default=8000, help="服务端口（默认 8000）")
    parser.add_argument("--no-browser", action="store_true", help="启动后不打开浏览器")
    parser.add_argument("--reset", action="store_true",
                        help="清空本机数据并重新部署（恢复内置题库）")
    parser.add_argument("--reinstall", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--console", action="store_true",
                        help="命令行模式（仅源码运行有效；exe 无控制台窗口）")
    parser.add_argument("--version", action="store_true", help="显示版本号")
    return parser.parse_args(argv)


def message_box(text, title=None, error=False):
    """无控制台 exe 里弹窗（不依赖 tkinter，启动早期也能用）"""
    try:
        import ctypes
        flags = 0x10 if error else 0x40   # MB_ICONERROR / MB_ICONINFORMATION
        ctypes.windll.user32.MessageBoxW(0, text, title or APP_NAME, flags)
        return True
    except Exception:
        return False


def show_crash(message):
    """GUI 都起不来时的兜底：写日志 + 系统弹窗"""
    append_log_file("FATAL\n" + message)
    message_box("部署器启动失败：\n\n%s\n\n日志：%s" % (message[:800], LOG_PATH),
                "%s 本地部署器" % APP_NAME, error=True)


def main(argv=None):
    # 打包成无控制台 exe 时 sys.stdout / sys.stderr 是 None，
    # 先兜底重定向到部署日志，避免任何 print 触发 AttributeError
    if sys.stdout is None:
        sys.stdout = QueueWriter(lambda line: append_log_file(line))
    if sys.stderr is None:
        sys.stderr = sys.stdout

    args = parse_args(argv)
    if os.name == "nt":
        # PyInstaller 单文件在少数场景会用到多进程，这行可避免子进程重复启动界面
        try:
            import multiprocessing
            multiprocessing.freeze_support()
        except Exception:
            pass

    if args.port < 1 or args.port > 65535:
        print("端口不合法：%d" % args.port)
        return 2

    if args.version:
        print("%s %s" % (APP_NAME, VERSION))
        if getattr(sys, "frozen", False):
            message_box("%s 本地部署器\n版本 v%s\n\n数据目录：%s"
                        % (APP_NAME, VERSION, DATA_ROOT))
        return 0

    if args.console:
        if getattr(sys, "frozen", False):
            # 打包成 windowed exe 后没有控制台，--console 会静默卡住，
            # 这种情况直接回落到图形界面，避免用户以为程序坏了
            print("exe 为无控制台窗口程序，--console 已忽略，改为图形界面")
            args.console = False
        else:
            return run_console(args)
    try:
        return run_gui(args)
    except Exception:
        detail = traceback.format_exc()
        if args.console:
            raise
        show_crash(detail)
        return 1


if __name__ == "__main__":
    sys.exit(main())
